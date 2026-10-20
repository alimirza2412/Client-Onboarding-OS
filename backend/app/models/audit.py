import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.database.base import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    log_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EmailLog(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Where the mocked EmailProvider "sends" mail for the demo — see
    app/services/email.py. Doubles as a minimal stand-in for the
    architecture's `email_events` table.
    """

    __tablename__ = "email_log"

    onboarding_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("onboarding_instances.id", ondelete="SET NULL"), nullable=True
    )
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
