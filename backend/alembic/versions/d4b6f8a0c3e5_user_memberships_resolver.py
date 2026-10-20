"""user memberships resolver function

Revises: c3a5e7f9b1d2

Same bootstrapping problem as the portal token resolver (see
c3a5e7f9b1d2_portal_token_resolver.py): finding out "which
organizations does this authenticated user belong to" is inherently a
cross-tenant lookup — you don't know the org yet, which is exactly what
RLS needs to allow the query. A SECURITY DEFINER function is the
standard, narrow way to allow just this one lookup, scoped to rows
belonging to the given user_id (not an open bypass of the table).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4b6f8a0c3e5'
down_revision: Union[str, Sequence[str], None] = 'c3a5e7f9b1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION list_user_memberships(p_user_id uuid)
        RETURNS TABLE(
            organization_id uuid,
            organization_name text,
            role text
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT om.organization_id, o.name, om.role::text
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            WHERE om.user_id = p_user_id;
        $$;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION list_user_memberships(uuid) TO onboarding_app;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS list_user_memberships(uuid);")
