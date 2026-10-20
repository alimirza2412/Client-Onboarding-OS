"""
SQLAlchemy engine and session configuration.

This wires up the connection to PostgreSQL so Phase 1 can start creating
models and running migrations. `pool_pre_ping` is enabled so stale
connections are detected rather than surfacing confusing errors later.

No queries are made at import time, so the app can start even if the
database isn't running yet (only relevant once code actually calls
`get_db`, which no endpoint does in Phase 0).
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a plain database session per request,
    with NO tenant context set. Only safe for endpoints that don't touch
    tenant-owned tables (e.g. auth/registration, before an org exists).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, organization_id) -> None:
    """
    Sets the PostgreSQL session variable RLS policies check against.

    IMPORTANT: this uses `SET LOCAL`, which only lasts for the current
    transaction — but a single request often does more than one
    transaction (e.g. commit(), then refresh() issues a new SELECT in a
    new auto-begun transaction). A one-shot SET LOCAL would silently stop
    applying after the first commit(). To handle this correctly, we
    register an `after_begin` listener on this session so the GUC is
    re-applied at the start of *every* transaction for the lifetime of
    this session — not just the first.

    We ALSO apply it immediately below: if a transaction is already in
    progress on this session (e.g. an earlier query auto-began one before
    we knew the org), registering the listener alone won't retroactively
    apply to that already-open transaction — `after_begin` only fires
    when a *new* transaction starts.
    """
    org_id_str = str(organization_id)

    def _reapply_on_begin(session, transaction, connection) -> None:
        connection.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": org_id_str})

    event.listen(db, "after_begin", _reapply_on_begin)
    db.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": org_id_str})
