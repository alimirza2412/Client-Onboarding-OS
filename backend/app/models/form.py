import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.database.base import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Form(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "forms"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    versions: Mapped[list["FormVersion"]] = relationship(
        back_populates="form", cascade="all, delete-orphan", order_by="FormVersion.version_number"
    )


class FormVersion(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Forms are immutable once published (docs/architecture.md, Phase 4).

    `schema` holds field definitions + simple conditional-logic rules as
    JSON, combining what the full architecture splits into separate
    form_fields rows — a deliberate demo simplification (see
    CHANGELOG.md). Example schema:

        {
          "fields": [
            {"key": "company_name", "label": "Company name", "type": "text", "required": true},
            {"key": "service", "label": "Service", "type": "select",
             "options": ["Paid Ads", "SEO", "Web Dev"], "required": true},
            {"key": "ad_budget", "label": "Monthly ad budget", "type": "number",
             "show_if": {"field": "service", "equals": "Paid Ads"}}
          ]
        }
    """

    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("form_id", "version_number", name="uq_form_version"),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    form: Mapped["Form"] = relationship(back_populates="versions")


class FormSubmission(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Pins to a specific form_version_id so editing/publishing a new form
    version never changes what an in-progress onboarding sees or has
    already submitted (Phase 4 critical test).
    """

    __tablename__ = "form_submissions"

    onboarding_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    form_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("form_versions.id", ondelete="RESTRICT"), nullable=False
    )
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
