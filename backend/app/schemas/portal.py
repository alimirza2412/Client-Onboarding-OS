import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import OnboardingInstanceStatus
from app.schemas.document import DocumentRequestOut
from app.schemas.onboarding import IntegrationAccountOut


class PortalMissingInfoOut(BaseModel):
    """
    Client-safe view of missing-information status (Task 5). Deliberately
    narrower than MissingInfoResult (app/schemas/ai.py) — no
    ai_intake_analysis, no internal staff-only detail, just what the
    client still needs to do.
    """

    progress_percent: int
    missing_fields: list[str]
    missing_documents: list[str]
    next_action: str


class PortalStatusOut(BaseModel):
    id: uuid.UUID
    client_name: str
    status: OnboardingInstanceStatus
    current_step: str
    kickoff_scheduled_at: datetime | None
    intake_submitted: bool
    intake_form: dict | None  # the published form_version.definition, if not yet submitted
    missing_info: PortalMissingInfoOut | None = None
    document_requests: list[DocumentRequestOut] = []
    integration_accounts: list[IntegrationAccountOut] = []
