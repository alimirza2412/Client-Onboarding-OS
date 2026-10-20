"""
Shared mixins for models.

TenantMixin adds `organization_id` to every tenant-owned table, per
architecture decision D2 (application-level filtering + PostgreSQL RLS).
Tables using this mixin also get a matching RLS policy in the initial
migration — see alembic/versions/0001_initial_schema.py.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TenantMixin:
    """Every tenant-owned table has organization_id. See docs/decisions.md."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
