import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db, set_tenant_context
from app.models.enums import MemberRole
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.schemas.auth import LoginRequest, MembershipOut, RegisterRequest, TokenResponse, UserOut
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "org"
    return base


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")

    slug_base = _slugify(payload.organization_name)
    slug = slug_base
    suffix = 1
    while db.query(Organization).filter(Organization.slug == slug).first() is not None:
        suffix += 1
        slug = f"{slug_base}-{suffix}"

    org = Organization(name=payload.organization_name, slug=slug)
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(org)
    db.add(user)
    db.flush()  # assigns org.id / user.id without committing yet

    # organization_members is RLS-protected (decision D2) — set the tenant
    # context to the org we just created before inserting into it.
    set_tenant_context(db, org.id)
    membership = OrganizationMember(
        organization_id=org.id, user_id=user.id, role=MemberRole.OWNER
    )
    db.add(membership)
    db.commit()

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    rows = db.execute(
        text("SELECT * FROM list_user_memberships(:user_id)"),
        {"user_id": str(current_user.id)},
    ).all()
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        memberships=[
            MembershipOut(organization_id=r.organization_id, organization_name=r.organization_name, role=MemberRole(r.role))
            for r in rows
        ],
    )
