import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_tenant_db, require_admin_or_above
from app.models.form import Form, FormVersion
from app.schemas.form import FormCreate, FormOut, FormVersionCreate, FormVersionOut

router = APIRouter(prefix="/forms", tags=["forms"])


@router.get("", response_model=list[FormOut])
def list_forms(
    db: Session = Depends(get_tenant_db),
    _=Depends(require_admin_or_above),
) -> list[Form]:
    return db.query(Form).options(joinedload(Form.versions)).order_by(Form.created_at.desc()).all()


@router.post("", response_model=FormOut, status_code=status.HTTP_201_CREATED)
def create_form(
    payload: FormCreate,
    db: Session = Depends(get_tenant_db),
    membership=Depends(require_admin_or_above),
) -> Form:
    """Creates a form and its first version (v1), published immediately."""
    form = Form(organization_id=membership.organization_id, name=payload.name)
    db.add(form)
    db.flush()

    version = FormVersion(
        organization_id=membership.organization_id,
        form_id=form.id,
        version_number=1,
        definition=payload.definition.model_dump(),
        is_published=True,
    )
    db.add(version)
    db.commit()
    db.refresh(form)
    return form


@router.post(
    "/{form_id}/versions", response_model=FormVersionOut, status_code=status.HTTP_201_CREATED
)
def publish_new_version(
    form_id: uuid.UUID,
    payload: FormVersionCreate,
    db: Session = Depends(get_tenant_db),
    membership=Depends(require_admin_or_above),
) -> FormVersion:
    """
    Publishes a new, immutable version. Existing onboarding instances
    keep referencing whichever form_version_id they already started on
    (see FormSubmission.form_version_id) — editing here never touches
    past submissions. This is the Phase 4 critical test.
    """
    form = db.query(Form).filter(Form.id == form_id).first()
    if form is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Form not found")

    latest = (
        db.query(FormVersion)
        .filter(FormVersion.form_id == form_id)
        .order_by(FormVersion.version_number.desc())
        .first()
    )
    next_version_number = (latest.version_number + 1) if latest else 1

    version = FormVersion(
        organization_id=membership.organization_id,
        form_id=form_id,
        version_number=next_version_number,
        definition=payload.definition.model_dump(),
        is_published=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/{form_id}/versions/latest", response_model=FormVersionOut)
def get_latest_published_version(
    form_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_admin_or_above),
) -> FormVersion:
    version = (
        db.query(FormVersion)
        .filter(FormVersion.form_id == form_id, FormVersion.is_published.is_(True))
        .order_by(FormVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published version for this form")
    return version
