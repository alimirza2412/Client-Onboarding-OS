import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MemberRole


class RegisterRequest(BaseModel):
    """
    Registering creates a brand-new organization with the registering
    user as its OWNER — the simplest possible "sign up your agency" flow
    for a demo. Inviting additional teammates isn't implemented (see
    CHANGELOG.md); seed_demo.py creates extra demo users directly.
    """

    organization_name: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MembershipOut(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: MemberRole

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    memberships: list[MembershipOut]

    model_config = {"from_attributes": True}
