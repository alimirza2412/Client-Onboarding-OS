from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db, require_staff_or_above
from app.models.enums import OnboardingInstanceStatus
from app.models.onboarding import OnboardingInstance

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> dict:
    counts = dict(
        db.query(OnboardingInstance.status, func.count(OnboardingInstance.id))
        .group_by(OnboardingInstance.status)
        .all()
    )

    completed = (
        db.query(OnboardingInstance)
        .filter(OnboardingInstance.status == OnboardingInstanceStatus.COMPLETED)
        .filter(OnboardingInstance.started_at.isnot(None))
        .filter(OnboardingInstance.completed_at.isnot(None))
        .all()
    )
    avg_time_to_start_hours = None
    if completed:
        total_seconds = sum(
            (i.completed_at - i.started_at).total_seconds() for i in completed
        )
        avg_time_to_start_hours = round(total_seconds / len(completed) / 3600, 2)

    instances = (
        db.query(OnboardingInstance)
        .order_by(OnboardingInstance.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "active_count": counts.get(OnboardingInstanceStatus.IN_PROGRESS, 0),
        "blocked_count": counts.get(OnboardingInstanceStatus.BLOCKED, 0),
        "completed_count": counts.get(OnboardingInstanceStatus.COMPLETED, 0),
        "not_started_count": counts.get(OnboardingInstanceStatus.NOT_STARTED, 0),
        "avg_time_to_start_hours": avg_time_to_start_hours,
        "instances": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "status": i.status.value,
                "current_step": i.current_step,
                "started_at": i.started_at.isoformat() if i.started_at else None,
                "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            }
            for i in instances
        ],
    }
