import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import IntegrationProvider, IntegrationStatus, OnboardingInstanceStatus
from app.schemas.document import DocumentRequestOut


class OnboardingInstanceCreate(BaseModel):
    client_id: uuid.UUID
    template_id: uuid.UUID


class IntegrationAccountOut(BaseModel):
    provider: IntegrationProvider
    status: IntegrationStatus
    connected_at: datetime | None

    model_config = {"from_attributes": True}


class OnboardingInstanceOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    status: OnboardingInstanceStatus
    current_step: str
    started_at: datetime | None
    completed_at: datetime | None
    kickoff_scheduled_at: datetime | None
    kickoff_brief: dict | None
    intake_answers: dict | None
    ai_intake_analysis: dict | None
    missing_info: dict | None
    document_requests: list[DocumentRequestOut] = []
    integration_accounts: list[IntegrationAccountOut] = []

    model_config = {"from_attributes": True}


class IntakeFormSubmit(BaseModel):
    answers: dict


class OAuthConnectRequest(BaseModel):
    provider: IntegrationProvider
