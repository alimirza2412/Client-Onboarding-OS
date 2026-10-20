"""
SQLAlchemy declarative base.

Business models (Phase 1 onward) will subclass `Base` here. No tables are
defined in Phase 0 — this file only establishes the base class so Alembic
has a target to track once models exist.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
