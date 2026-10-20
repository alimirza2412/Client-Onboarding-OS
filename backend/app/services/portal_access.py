"""
Resolves a client-portal access token to a tenant-scoped DB session.

Two-step process, mirroring the SECURITY DEFINER function added in
alembic/versions/c3a5e7f9b1d2_portal_token_resolver.py:

  1. Look up (instance_id, organization_id) for the token via
     resolve_portal_token() — this one call is allowed to bypass RLS
     (that's the whole point of the function), because at this point we
     don't yet know which organization the request belongs to.
  2. Once we know the organization, open a normal session and set the
     RLS tenant context on it — every other query in the request goes
     through RLS exactly like a staff request would.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, set_tenant_context


def resolve_portal_session(token: str) -> tuple[Session, uuid.UUID]:
    """Returns (tenant_scoped_db_session, instance_id) or raises 404."""
    lookup_db = SessionLocal()
    try:
        row = lookup_db.execute(
            text("SELECT * FROM resolve_portal_token(:token)"), {"token": token}
        ).first()
    finally:
        lookup_db.close()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid portal link")

    instance_id, organization_id = row

    db = SessionLocal()
    set_tenant_context(db, organization_id)
    return db, instance_id
