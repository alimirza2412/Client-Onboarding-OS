import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.enums import ClientStatus
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Client(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ClientStatus] = mapped_column(
        SAEnum(ClientStatus, name="client_status"),
        nullable=False,
        default=ClientStatus.LEAD,
    )

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class Contact(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "contacts"

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client: Mapped["Client"] = relationship(back_populates="contacts")
