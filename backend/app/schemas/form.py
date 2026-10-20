import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FormFieldSchema(BaseModel):
    key: str
    label: str
    type: str  # text | number | email | phone | select | multi-select | checkbox | date | file | long_text
    required: bool = False
    options: list[str] | None = None
    show_if: dict | None = None  # {"field": "...", "equals": "..."}


class FormVersionDefinition(BaseModel):
    fields: list[FormFieldSchema]


class FormCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    definition: FormVersionDefinition


class FormVersionCreate(BaseModel):
    definition: FormVersionDefinition


class FormVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    definition: dict
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FormOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    versions: list[FormVersionOut] = []

    model_config = {"from_attributes": True}
