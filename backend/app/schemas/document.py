import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DocumentRequestStatus, DocumentReviewStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    uploaded_at: datetime
    ai_extracted_data: dict | None
    ai_confidence: float | None
    review_status: DocumentReviewStatus

    model_config = {"from_attributes": True}


class DocumentRequestOut(BaseModel):
    id: uuid.UUID
    name: str
    status: DocumentRequestStatus
    documents: list[DocumentOut] = []

    model_config = {"from_attributes": True}
