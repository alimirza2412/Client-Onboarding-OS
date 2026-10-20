import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.database.base import Base
from app.models.enums import DocumentRequestStatus, DocumentReviewStatus
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentRequest(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "document_requests"

    onboarding_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentRequestStatus] = mapped_column(
        SAEnum(DocumentRequestStatus, name="document_request_status"),
        nullable=False,
        default=DocumentRequestStatus.REQUESTED,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="document_request", cascade="all, delete-orphan"
    )


class Document(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    An uploaded file plus its AI extraction result. Combines what the
    full architecture splits into `documents` + `document_versions` into
    a single row per upload — a demo simplification (see CHANGELOG.md);
    re-uploads create a new row rather than a new version of the same one.

    Files are stored on local disk under `backend/uploads/` rather than
    S3/MinIO for demo simplicity (see docs/decisions.md and DEMO_SETUP.md).
    """

    __tablename__ = "documents"

    document_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ai_extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[DocumentReviewStatus] = mapped_column(
        SAEnum(DocumentReviewStatus, name="document_review_status"),
        nullable=False,
        default=DocumentReviewStatus.PENDING,
    )

    document_request: Mapped["DocumentRequest"] = relationship(back_populates="documents")
