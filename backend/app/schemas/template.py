import uuid

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    form_id: uuid.UUID | None = None
    required_documents: list[str] = Field(default_factory=list)


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    form_id: uuid.UUID | None
    required_documents: list[str]
    is_default: bool

    model_config = {"from_attributes": True}
