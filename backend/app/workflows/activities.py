"""
Temporal activities for the onboarding workflow (Phase 7).

Activities do all the actual work (DB writes, "sending" email, calling
the AI service) — the workflow itself only orchestrates *when* these run
and waits for human actions via signals. This split is what keeps the
workflow function deterministic/replayable, which Temporal requires.

Each activity opens its own short-lived DB session and explicitly sets
the RLS tenant context (decision D2) — the worker process uses the same
non-owner `onboarding_app` role as the API, so RLS applies here too, not
just to HTTP requests.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from temporalio import activity

from app.database.session import SessionLocal, set_tenant_context
from app.models.document import Document, DocumentRequest
from app.models.enums import (
    DocumentRequestStatus,
    DocumentReviewStatus,
    OnboardingInstanceStatus,
)
from app.models.form import FormSubmission, FormVersion
from app.models.onboarding import OnboardingInstance
from app.services.ai import analyze_intake, extract_document_data
from app.services.email import (
    email_provider,
    kickoff_reminder_body,
    onboarding_complete_body,
    welcome_email_body,
)
from app.services.missing_info import detect_missing_information

logger = logging.getLogger("onboarding-worker")

# Confidence below this threshold routes a document to human review rather
# than auto-approving it (Phase 10 requirement).
AI_CONFIDENCE_THRESHOLD = 0.75


def _session(organization_id: str):
    db = SessionLocal()
    set_tenant_context(db, uuid.UUID(organization_id))
    return db


@activity.defn
async def update_instance_step(
    instance_id: str, organization_id: str, step: str, mark_status: str | None = None
) -> None:
    db = _session(organization_id)
    try:
        instance = db.get(OnboardingInstance, uuid.UUID(instance_id))
        if instance is not None:
            instance.current_step = step
            if mark_status is not None:
                instance.status = OnboardingInstanceStatus(mark_status)
            elif instance.status == OnboardingInstanceStatus.NOT_STARTED:
                instance.status = OnboardingInstanceStatus.IN_PROGRESS
            db.commit()
    finally:
        db.close()


@activity.defn
async def analyze_intake_and_detect_missing(instance_id: str, organization_id: str) -> None:
    """
    Tasks 1 + 2 + 3 + 6. Runs once, right after the client submits the
    intake form (see app/workflows/onboarding.py). Two independent
    pieces of work, kept clearly separate per Task 2's instruction not
    to let AI decide what's "missing":

      1. AI Intake Analysis (app.services.ai.analyze_intake) — drafts a
         staff-facing summary. Has its own internal mock fallback and
         never raises.
      2. Missing Information Detection (app.services.missing_info) —
         deterministic, schema-based, no AI involved at all.

    Both results are stored on the OnboardingInstance (Task 3 — reusing
    the same JSON-column pattern as the existing kickoff_brief field,
    see app/models/onboarding.py).

    Wrapped in a try/except so a failure here (e.g. a DB hiccup) can
    never break the onboarding workflow (Task 6) — the workflow's next
    steps (document collection, OAuth, kickoff) proceed regardless of
    whether this activity fully succeeded.
    """
    db = _session(organization_id)
    try:
        instance = db.get(OnboardingInstance, uuid.UUID(instance_id))
        if instance is None:
            return

        answers = instance.intake_answers or {}

        # --- 1. AI Intake Analysis (Groq, with mock fallback) ---
        analysis_result, source = analyze_intake(answers)
        analysis_dict = analysis_result.model_dump()
        analysis_dict["generated_by"] = source
        instance.ai_intake_analysis = analysis_dict

        # --- 2. Missing Information Detection (deterministic, no AI) ---
        submission = (
            db.query(FormSubmission)
            .filter(FormSubmission.onboarding_instance_id == instance.id)
            .order_by(FormSubmission.submitted_at.desc())
            .first()
        )
        form_definition = None
        if submission and submission.form_version_id:
            version = db.get(FormVersion, submission.form_version_id)
            if version:
                form_definition = version.definition

        document_requests = (
            db.query(DocumentRequest)
            .filter(DocumentRequest.onboarding_instance_id == instance.id)
            .all()
        )
        missing_result = detect_missing_information(form_definition, answers, document_requests)
        instance.missing_info = missing_result.model_dump()

        db.commit()
    except Exception as exc:  # noqa: BLE001 — deliberate: must never break the workflow
        db.rollback()
        logger.warning("analyze_intake_and_detect_missing failed for instance %s: %s", instance_id, exc)
    finally:
        db.close()


@activity.defn
async def send_welcome_email(
    instance_id: str, organization_id: str, client_name: str, client_email: str
) -> None:
    db = _session(organization_id)
    try:
        email_provider.send(
            db=db,
            organization_id=uuid.UUID(organization_id),
            to_address=client_email,
            subject="Welcome! Let's get your onboarding started",
            body=welcome_email_body(client_name),
            onboarding_instance_id=uuid.UUID(instance_id),
        )
    finally:
        db.close()


@activity.defn
async def send_reminder_email(
    instance_id: str, organization_id: str, client_name: str, client_email: str, what: str
) -> None:
    """
    Demonstrates the reminder pattern from docs/research.md (24h/48h/72h
    escalation). The demo uses a short delay instead of real hours — see
    app/workflows/onboarding.py and DEMO_SETUP.md — but the Temporal
    timer + signal race mechanics are the real thing, not simulated.
    """
    db = _session(organization_id)
    try:
        email_provider.send(
            db=db,
            organization_id=uuid.UUID(organization_id),
            to_address=client_email,
            subject=f"Reminder: {what} still needed",
            body=kickoff_reminder_body(client_name),
            onboarding_instance_id=uuid.UUID(instance_id),
        )
    finally:
        db.close()


@activity.defn
async def process_documents_ai(instance_id: str, organization_id: str) -> None:
    """
    Runs AI extraction on every pending document for this onboarding
    instance's document requests, then marks each request VERIFIED (or
    leaves it flagged for human review — never silently auto-completes a
    low-confidence extraction, per docs/architecture.md).
    """
    db = _session(organization_id)
    try:
        requests = (
            db.query(DocumentRequest)
            .filter(DocumentRequest.onboarding_instance_id == uuid.UUID(instance_id))
            .all()
        )
        for req in requests:
            for doc in req.documents:
                if doc.review_status != DocumentReviewStatus.PENDING:
                    continue
                try:
                    with open(doc.storage_path, "rb") as f:
                        raw = f.read(4000)
                    text = raw.decode("utf-8", errors="ignore")
                except OSError:
                    text = doc.original_filename

                data, confidence = extract_document_data(text or doc.original_filename)
                doc.ai_extracted_data = data
                doc.ai_confidence = confidence
                doc.review_status = (
                    DocumentReviewStatus.AUTO_APPROVED
                    if confidence >= AI_CONFIDENCE_THRESHOLD
                    else DocumentReviewStatus.NEEDS_REVIEW
                )
            req.status = DocumentRequestStatus.VERIFIED
        db.commit()
    finally:
        db.close()


@activity.defn
async def schedule_kickoff(instance_id: str, organization_id: str) -> str:
    db = _session(organization_id)
    try:
        instance = db.get(OnboardingInstance, uuid.UUID(instance_id))
        scheduled = datetime.now(timezone.utc) + timedelta(days=3)
        if instance is not None:
            instance.kickoff_scheduled_at = scheduled
            db.commit()
        return scheduled.isoformat()
    finally:
        db.close()


@activity.defn
async def generate_kickoff_brief(instance_id: str, organization_id: str) -> dict:
    """
    Drafts a kickoff brief from the intake answers + document extractions
    collected so far. Uses the same AI service as document extraction —
    with the same mock fallback if GROQ_API_KEY isn't set. This is
    advisory content for the team, never authoritative workflow state.
    """
    db = _session(organization_id)
    try:
        instance = db.get(OnboardingInstance, uuid.UUID(instance_id))
        if instance is None:
            return {}

        requests = (
            db.query(DocumentRequest)
            .filter(DocumentRequest.onboarding_instance_id == uuid.UUID(instance_id))
            .all()
        )
        doc_facts: list[str] = []
        for req in requests:
            for doc in req.documents:
                if doc.ai_extracted_data:
                    doc_facts.extend(doc.ai_extracted_data.get("key_facts", []))

        answers = instance.intake_answers or {}
        summary_text = "Intake answers: " + ", ".join(
            f"{k}={v}" for k, v in answers.items()
        )
        if doc_facts:
            summary_text += " | Document facts: " + "; ".join(doc_facts)

        extracted, _confidence = extract_document_data(summary_text)

        brief = {
            "client_overview": extracted.get("company_name") or "New client",
            "goals": answers.get("goals") or answers.get("service") or "Not specified",
            "requirements": answers,
            "document_facts": doc_facts,
            "missing_information": [] if answers else ["Intake form answers were empty"],
            "next_steps": [
                "Confirm kickoff call time with client",
                "Assign delivery team",
                "Review any documents flagged for manual review",
            ],
            "generated_by": "groq" if extracted.get("_source") == "groq" else "mock-ai",
        }

        instance.kickoff_brief = brief
        db.commit()
        return brief
    finally:
        db.close()


@activity.defn
async def mark_complete(
    instance_id: str, organization_id: str, client_name: str, client_email: str
) -> None:
    db = _session(organization_id)
    try:
        instance = db.get(OnboardingInstance, uuid.UUID(instance_id))
        if instance is not None:
            instance.status = OnboardingInstanceStatus.COMPLETED
            instance.completed_at = datetime.now(timezone.utc)
            instance.current_step = "onboarding_complete"
            db.commit()

        email_provider.send(
            db=db,
            organization_id=uuid.UUID(organization_id),
            to_address=client_email,
            subject="You're all set — onboarding complete!",
            body=onboarding_complete_body(client_name),
            onboarding_instance_id=uuid.UUID(instance_id),
        )
    finally:
        db.close()


@activity.defn
async def complete_workflow_execution_record(instance_id: str, organization_id: str) -> None:
    from app.models.onboarding import WorkflowExecution
    from app.models.enums import WorkflowExecutionStatus

    db = _session(organization_id)
    try:
        record = (
            db.query(WorkflowExecution)
            .filter(WorkflowExecution.onboarding_instance_id == uuid.UUID(instance_id))
            .order_by(WorkflowExecution.started_at.desc())
            .first()
        )
        if record is not None:
            record.status = WorkflowExecutionStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
