import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.enums import IntegrationProvider, IntegrationStatus
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationAccount(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Represents a connected third-party account (Google/Meta).

    No real OAuth flow or tokens for the demo — connecting is mocked
    (see app/services/integrations.py and docs/decisions.md /
    CHANGELOG.md for why real OAuth is out of scope for a 2-day demo).
    """

    __tablename__ = "integration_accounts"

    onboarding_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        SAEnum(IntegrationProvider, name="integration_provider"), nullable=False
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        SAEnum(IntegrationStatus, name="integration_status"),
        nullable=False,
        default=IntegrationStatus.NOT_CONNECTED,
    )
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
