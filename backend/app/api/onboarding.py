import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_tenant_db, require_staff_or_above
from app.config.settings import get_settings
from app.models.client import Client
from app.models.document import DocumentRequest
from app.models.enums import WorkflowExecutionStatus
from app.models.onboarding import OnboardingInstance, OnboardingTemplate, WorkflowExecution
from app.schemas.onboarding import OnboardingInstanceCreate, OnboardingInstanceOut
from app.services.missing_info import compute_current_missing_info
from app.services.temporal_client import get_temporal_client
from app.workflows.onboarding import OnboardingWorkflow, OnboardingWorkflowInput

router = APIRouter(prefix="/onboarding-instances", tags=["onboarding"])
settings = get_settings()


@router.get("", response_model=list[OnboardingInstanceOut])
def list_instances(
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> list[OnboardingInstance]:
    return (
        db.query(OnboardingInstance)
        .options(
            joinedload(OnboardingInstance.document_requests).joinedload(DocumentRequest.documents),
            joinedload(OnboardingInstance.integration_accounts),
        )
        .order_by(OnboardingInstance.created_at.desc())
        .all()
    )


@router.get("/{instance_id}", response_model=OnboardingInstanceOut)
def get_instance(
    instance_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> OnboardingInstance:
    instance = (
        db.query(OnboardingInstance)
        .options(
            joinedload(OnboardingInstance.document_requests).joinedload(DocumentRequest.documents),
            joinedload(OnboardingInstance.integration_accounts),
        )
        .filter(OnboardingInstance.id == instance_id)
        .first()
    )
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding instance not found")

    # Live-recompute rather than trust the stored snapshot: documents
    # keep getting uploaded after the intake-time snapshot was written,
    # so the stored value alone would look stale/wrong on this page.
    # The stored column (Task 3) remains the point-in-time audit record.
    if instance.intake_answers is not None:
        instance.missing_info = compute_current_missing_info(db, instance).model_dump()

    return instance


@router.get("/{instance_id}/portal-link")
def get_portal_link(
    instance_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> dict:
    instance = db.query(OnboardingInstance).filter(OnboardingInstance.id == instance_id).first()
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding instance not found")
    return {"portal_path": f"/portal/{instance.portal_token}"}


@router.get("/{instance_id}/workflow-status")
async def get_live_workflow_status(
    instance_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> dict:
    """
    Queries the *live* Temporal workflow directly (not just the mirrored
    DB fields) — demonstrates that the workflow is genuinely running and
    reachable, not just a DB row. See DEMO_SETUP.md for how to verify
    this survives a worker restart.
    """
    instance = db.query(OnboardingInstance).filter(OnboardingInstance.id == instance_id).first()
    if instance is None or instance.temporal_workflow_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No workflow associated with this instance")

    client = await get_temporal_client()
    handle = client.get_workflow_handle(instance.temporal_workflow_id)
    try:
        live_status = await handle.query(OnboardingWorkflow.status)
    except Exception as exc:  # workflow already completed, or worker not running
        return {"queryable": False, "detail": str(exc)}
    return {"queryable": True, "live_status": live_status}


@router.post("", response_model=OnboardingInstanceOut, status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: OnboardingInstanceCreate,
    db: Session = Depends(get_tenant_db),
    membership=Depends(require_staff_or_above),
) -> OnboardingInstance:
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")

    template = (
        db.query(OnboardingTemplate).filter(OnboardingTemplate.id == payload.template_id).first()
    )
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding template not found")

    primary_contact = next((c for c in client.contacts if c.is_primary), None) or (
        client.contacts[0] if client.contacts else None
    )
    if primary_contact is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Client has no contact to send onboarding emails to"
        )

    instance = OnboardingInstance(
        organization_id=membership.organization_id,
        client_id=client.id,
        template_id=template.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(instance)
    db.flush()

    for doc_name in template.required_documents or []:
        db.add(
            DocumentRequest(
                organization_id=membership.organization_id,
                onboarding_instance_id=instance.id,
                name=doc_name,
            )
        )
    db.commit()
    db.refresh(instance)

    workflow_id = f"onboarding-{instance.id}"
    temporal_client = await get_temporal_client()
    handle = await temporal_client.start_workflow(
        OnboardingWorkflow.run,
        OnboardingWorkflowInput(
            instance_id=str(instance.id),
            organization_id=str(membership.organization_id),
            client_name=client.name,
            client_email=primary_contact.email,
            required_document_names=template.required_documents or [],
        ),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    instance.temporal_workflow_id = workflow_id
    db.add(
        WorkflowExecution(
            organization_id=membership.organization_id,
            onboarding_instance_id=instance.id,
            temporal_workflow_id=workflow_id,
            temporal_run_id=handle.first_execution_run_id or "",
            status=WorkflowExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(instance)
    return instance
