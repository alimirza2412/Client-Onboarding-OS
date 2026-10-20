from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db, require_admin_or_above
from app.models.onboarding import OnboardingTemplate
from app.schemas.template import TemplateCreate, TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_tenant_db),
    _=Depends(require_admin_or_above),
) -> list[OnboardingTemplate]:
    return db.query(OnboardingTemplate).order_by(OnboardingTemplate.created_at.desc()).all()


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_tenant_db),
    membership=Depends(require_admin_or_above),
) -> OnboardingTemplate:
    template = OnboardingTemplate(
        organization_id=membership.organization_id,
        name=payload.name,
        form_id=payload.form_id,
        required_documents=payload.required_documents,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
