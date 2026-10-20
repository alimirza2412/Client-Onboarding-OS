"""
Task 2 — Real Missing Information Detection.

Deliberately has NO dependency on app.services.ai or Groq — this is
plain, deterministic comparison logic:

    required form fields (from the SPECIFIC form_version the client was
    actually shown — not "latest", so this respects form-version
    immutability, Phase 4)
        +
    required documents (from the onboarding_template)
        +
    what's actually been submitted/uploaded
        =
    what's missing.

Two entry points:
  - detect_missing_information(): pure function, no I/O, easy to test.
  - compute_current_missing_info(): DB-aware wrapper used by the API
    layer to get a fresh/live result (see app/api/onboarding.py and
    app/api/portal.py) rather than reading the point-in-time snapshot
    stored on OnboardingInstance.missing_info (which is written once,
    right after intake submission — see
    app/workflows/activities.py:analyze_intake_and_detect_missing).
"""

from sqlalchemy.orm import Session

from app.models.document import DocumentRequest
from app.models.form import FormSubmission, FormVersion
from app.models.onboarding import OnboardingInstance
from app.schemas.ai import MissingInfoResult


def detect_missing_information(
    form_definition: dict | None,
    submitted_answers: dict | None,
    document_requests: list[DocumentRequest],
) -> MissingInfoResult:
    """
    Pure, deterministic. `form_definition` is a FormVersion.definition
    dict (`{"fields": [...]}`) or None if the template has no form.
    """
    answers = submitted_answers or {}
    fields = (form_definition or {}).get("fields", [])

    missing_fields: list[str] = []
    completed_fields: list[str] = []
    for field in fields:
        if not field.get("required"):
            continue

        # Respect conditional logic: a field hidden by show_if isn't
        # actually required unless its condition is met.
        show_if = field.get("show_if")
        if show_if and answers.get(show_if.get("field")) != show_if.get("equals"):
            continue

        label = field.get("label") or field.get("key", "field")
        value = answers.get(field.get("key"))
        if value in (None, "", []):
            missing_fields.append(label)
        else:
            completed_fields.append(label)

    missing_documents: list[str] = []
    completed_documents: list[str] = []
    for req in document_requests:
        if req.documents:
            completed_documents.append(req.name)
        else:
            missing_documents.append(req.name)

    total = len(missing_fields) + len(completed_fields) + len(missing_documents) + len(completed_documents)
    done = len(completed_fields) + len(completed_documents)
    progress_percent = round((done / total) * 100) if total else 100

    return MissingInfoResult(
        missing_fields=missing_fields,
        missing_documents=missing_documents,
        completed_fields=completed_fields,
        completed_documents=completed_documents,
        progress_percent=progress_percent,
    )


def compute_current_missing_info(db: Session, instance: OnboardingInstance) -> MissingInfoResult:
    """
    DB-aware wrapper: looks up the SPECIFIC form_version the client's
    submission referenced (not "latest published" — the instance may be
    on an older version if the form was edited since), plus the current
    document_requests, and runs detect_missing_information() fresh.

    If the intake form hasn't been submitted yet, there's no submission
    to compare against — in that case only documents are evaluated
    (fields are neither "missing" nor "complete" pre-submission).
    """
    form_definition = None
    if instance.intake_answers is not None:
        submission = (
            db.query(FormSubmission)
            .filter(FormSubmission.onboarding_instance_id == instance.id)
            .order_by(FormSubmission.submitted_at.desc())
            .first()
        )
        if submission and submission.form_version_id:
            version = db.get(FormVersion, submission.form_version_id)
            if version:
                form_definition = version.definition

    document_requests = (
        db.query(DocumentRequest)
        .filter(DocumentRequest.onboarding_instance_id == instance.id)
        .all()
    )

    return detect_missing_information(
        form_definition=form_definition,
        submitted_answers=instance.intake_answers,
        document_requests=document_requests,
    )
