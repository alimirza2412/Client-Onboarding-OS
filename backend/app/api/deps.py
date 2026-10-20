"""
Core request dependencies: who is calling (auth), which organization
they're acting in (tenant context), and whether their role permits the
action (RBAC).

RBAC here is a simple fixed-enum permission table rather than the full
architecture's dynamic roles/permissions tables — a deliberate demo
simplification (see docs/decisions.md and CHANGELOG.md). It still
enforces the Phase 2 rules: CLIENT cannot access admin functions, STAFF
cannot modify organization settings, ADMIN can manage clients, OWNER has
full permissions.
"""

import uuid
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db, set_tenant_context
from app.models.enums import MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.get(User, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


class ResolvedMembership:
    """
    Plain data holder for a resolved membership — deliberately NOT the
    OrganizationMember ORM model, since that row was looked up via the
    list_user_memberships() SECURITY DEFINER function (see
    alembic/versions/d4b6f8a0c3e5_user_memberships_resolver.py) rather
    than a normal RLS-scoped query, on a session that isn't tied to any
    particular request's tenant-scoped session.
    """

    def __init__(self, organization_id: uuid.UUID, organization_name: str, role: MemberRole):
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.role = role


def get_current_membership(
    current_user: User = Depends(get_current_user),
    x_organization_id: uuid.UUID | None = Header(default=None),
) -> ResolvedMembership:
    """
    Resolves which organization this request acts within. "Which orgs
    does this user belong to" is a cross-tenant lookup by nature (RLS
    can't help here — we don't know the org yet), so it goes through the
    list_user_memberships() SECURITY DEFINER function rather than a
    normal tenant-scoped query. Most demo users belong to exactly one
    organization, so this defaults to their first membership; pass
    `X-Organization-Id` to pick a specific one if a user belongs to more
    than one.
    """
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT * FROM list_user_memberships(:user_id)"),
            {"user_id": str(current_user.id)},
        ).all()
    finally:
        db.close()

    if not rows:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no organization membership")

    memberships = [
        ResolvedMembership(organization_id=r.organization_id, organization_name=r.organization_name, role=MemberRole(r.role))
        for r in rows
    ]

    if x_organization_id is not None:
        for m in memberships:
            if m.organization_id == x_organization_id:
                return m
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of that organization")

    return memberships[0]


def get_tenant_db(
    membership: ResolvedMembership = Depends(get_current_membership),
) -> Generator[Session, None, None]:
    """
    The main dependency tenant-scoped routes should use. Yields a DB
    session with PostgreSQL RLS's session variable set to the caller's
    organization (decision D2) — see app/database/session.py.
    """
    db = SessionLocal()
    try:
        set_tenant_context(db, membership.organization_id)
        yield db
    finally:
        db.close()


def require_roles(*allowed: MemberRole):
    """Dependency factory: 403s unless the caller's role is one of `allowed`."""

    def _check(membership: ResolvedMembership = Depends(get_current_membership)) -> ResolvedMembership:
        if membership.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role {membership.role.value} is not permitted to perform this action",
            )
        return membership

    return _check


# Convenience shorthands matching the Phase 2 test matrix
require_owner = require_roles(MemberRole.OWNER)
require_admin_or_above = require_roles(MemberRole.OWNER, MemberRole.ADMIN)
require_staff_or_above = require_roles(MemberRole.OWNER, MemberRole.ADMIN, MemberRole.STAFF)
