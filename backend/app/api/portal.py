import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.config.settings import get_settings
from app.models.document import Document, DocumentRequest
from app.models.enums import DocumentRequestStatus
from app.models.form import FormSubmission, FormVersion
from app.models.onboarding import OnboardingInstance, OnboardingTemplate
from app.schemas.onboarding import IntakeFormSubmit, OAuthConnectRequest
from app.schemas.portal import PortalMissingInfoOut, PortalStatusOut
from app.services.integrations import mock_connect
from app.services.missing_info import compute_current_missing_info
from app.services.portal_access import resolve_portal_session
from app.services.temporal_client import get_temporal_client

router = APIRouter(prefix="/portal", tags=["portal"])
settings = get_settings()


def _get_portal_db(token: str) -> tuple[Session, uuid.UUID]:
    return resolve_portal_session(token)


def _compute_next_action(
    intake_submitted: bool,
    missing_fields: list[str],
    missing_documents: list[str],
    connected_providers: set[str],
    onboarding_status: str,
) -> str:
    """Simple deterministic next-action text — no AI involved (Task 5: keep this simple)."""
    if onboarding_status == "COMPLETED":
        return "All done — we'll be in touch to schedule your kickoff call."
    if not intake_submitted:
        return "Complete the intake form."
    if missing_fields or missing_documents:
        return "Complete the missing information."
    if not {"GOOGLE", "META"} <= connected_providers:
        return "Connect your accounts."
    return "Sit tight — we're reviewing everything on our end."


@router.get("/{token}", response_model=PortalStatusOut)
def get_portal_status(token: str) -> PortalStatusOut:
    db, instance_id = _get_portal_db(token)
    try:
        instance = (
            db.query(OnboardingInstance)
            .options(
                joinedload(OnboardingInstance.client),
                joinedload(OnboardingInstance.document_requests).joinedload(
                    DocumentRequest.documents
                ),
                joinedload(OnboardingInstance.integration_accounts),
            )
            .filter(OnboardingInstance.id == instance_id)
            .first()
        )
        if instance is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding not found")

        already_submitted = instance.intake_answers is not None
        intake_form = None
        if not already_submitted:
            template = (
                db.query(OnboardingTemplate)
                .filter(OnboardingTemplate.id == instance.template_id)
                .first()
            )
            if template and template.form_id:
                version = (
                    db.query(FormVersion)
                    .filter(
                        FormVersion.form_id == template.form_id,
                        FormVersion.is_published.is_(True),
                    )
                    .order_by(FormVersion.version_number.desc())
                    .first()
                )
                if version:
                    intake_form = version.definition

        # Task 5: client-safe missing-info view. Live-recomputed, same as
        # the staff view — see app/services/missing_info.py. Only
        # meaningful once intake has been submitted (before that, the
        # intake form itself is the thing being shown).
        missing_info_out = None
        if already_submitted:
            live = compute_current_missing_info(db, instance)
            connected = {
                a.provider.value for a in instance.integration_accounts if a.status.value == "CONNECTED"
            }
            next_action = _compute_next_action(
                intake_submitted=True,
                missing_fields=live.missing_fields,
                missing_documents=live.missing_documents,
                connected_providers=connected,
                onboarding_status=instance.status.value,
            )
            missing_info_out = PortalMissingInfoOut(
                progress_percent=live.progress_percent,
                missing_fields=live.missing_fields,
                missing_documents=live.missing_documents,
                next_action=next_action,
            )

        return PortalStatusOut(
            id=instance.id,
            client_name=instance.client.name,
            status=instance.status,
            current_step=instance.current_step,
            kickoff_scheduled_at=instance.kickoff_scheduled_at,
            intake_submitted=already_submitted,
            intake_form=intake_form,
            missing_info=missing_info_out,
            document_requests=instance.document_requests,
            integration_accounts=instance.integration_accounts,
        )
    finally:
        db.close()


@router.post("/{token}/intake", status_code=status.HTTP_204_NO_CONTENT)
async def submit_intake(token: str, payload: IntakeFormSubmit) -> None:
    db, instance_id = _get_portal_db(token)
    try:
        instance = db.query(OnboardingInstance).filter(OnboardingInstance.id == instance_id).first()
        if instance is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding not found")
        if instance.intake_answers is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Intake form already submitted")

        template = (
            db.query(OnboardingTemplate)
            .filter(OnboardingTemplate.id == instance.template_id)
            .first()
        )
        form_version = None
        if template and template.form_id:
            form_version = (
                db.query(FormVersion)
                .filter(FormVersion.form_id == template.form_id, FormVersion.is_published.is_(True))
                .order_by(FormVersion.version_number.desc())
                .first()
            )

        instance.intake_answers = payload.answers
        if form_version:
            db.add(
                FormSubmission(
                    organization_id=instance.organization_id,
                    onboarding_instance_id=instance.id,
                    form_version_id=form_version.id,
                    answers=payload.answers,
                    submitted_at=datetime.now(timezone.utc),
                )
            )
        db.commit()

        if instance.temporal_workflow_id:
            temporal_client = await get_temporal_client()
            handle = temporal_client.get_workflow_handle(instance.temporal_workflow_id)
            await handle.signal("submit_intake_form")
    finally:
        db.close()


@router.post("/{token}/documents/{request_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(token: str, request_id: uuid.UUID, file: UploadFile = File(...)) -> dict:
    db, instance_id = _get_portal_db(token)
    try:
        instance = db.query(OnboardingInstance).filter(OnboardingInstance.id == instance_id).first()
        if instance is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding not found")

        doc_request = (
            db.query(DocumentRequest)
            .filter(
                DocumentRequest.id == request_id,
                DocumentRequest.onboarding_instance_id == instance_id,
            )
            .first()
        )
        if doc_request is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document request not found")

        uploads_root = Path(settings.uploads_dir) / str(instance_id)
        uploads_root.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{file.filename or 'upload'}"
        dest_path = uploads_root / safe_name

        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)

        document = Document(
            organization_id=instance.organization_id,
            document_request_id=doc_request.id,
            original_filename=file.filename or "upload",
            storage_path=str(dest_path),
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(document)
        doc_request.status = DocumentRequestStatus.UPLOADED
        db.commit()
        db.refresh(document)

        if instance.temporal_workflow_id:
            temporal_client = await get_temporal_client()
            handle = temporal_client.get_workflow_handle(instance.temporal_workflow_id)
            await handle.signal("upload_document", str(document.id))

        return {"document_id": str(document.id), "status": "uploaded"}
    finally:
        db.close()


@router.post("/{token}/oauth/connect", status_code=status.HTTP_200_OK)
async def connect_oauth(token: str, payload: OAuthConnectRequest) -> dict:
    """
    Mocked OAuth connect (Phase 9) — see app/services/integrations.py and
    docs/decisions.md for why this doesn't do a real OAuth redirect.
    """
    db, instance_id = _get_portal_db(token)
    try:
        instance = db.query(OnboardingInstance).filter(OnboardingInstance.id == instance_id).first()
        if instance is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding not found")

        account = mock_connect(db, instance.organization_id, instance_id, payload.provider)

        if instance.temporal_workflow_id:
            temporal_client = await get_temporal_client()
            handle = temporal_client.get_workflow_handle(instance.temporal_workflow_id)
            await handle.signal("connect_oauth", payload.provider.value)

        return {"provider": account.provider.value, "status": account.status.value}
    finally:
        db.close()
