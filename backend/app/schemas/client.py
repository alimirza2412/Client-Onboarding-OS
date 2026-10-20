import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ClientStatus


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    is_primary: bool = True


class ContactOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    is_primary: bool

    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact: ContactIn


class ClientUpdate(BaseModel):
    name: str | None = None
    status: ClientStatus | None = None


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str
    status: ClientStatus
    created_at: datetime
    contacts: list[ContactOut] = []

    model_config = {"from_attributes": True}
