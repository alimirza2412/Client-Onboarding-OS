"""portal token resolver function

Revises: b2f4c6a1d9e0

Client portal access (Phase 5) uses an opaque per-instance token instead
of a full separate client-login system (see docs/decisions.md,
CHANGELOG.md). Given RLS is enabled (previous migration), the API can't
just query `onboarding_instances WHERE portal_token = ...` to find out
which organization a token belongs to — it doesn't know the org yet,
which is exactly what RLS needs to allow the query in the first place.

This is a standard, narrow way to solve that bootstrapping problem: a
SECURITY DEFINER function, owned by the migration/owner role, that looks
up ONLY (instance_id, organization_id) by token. SECURITY DEFINER
functions run with the *owner's* privileges, so this one lookup bypasses
RLS — everything else the app does afterward still goes through the
normal RLS-enforced session once the org is known. The token itself
(a random 32-byte hex value) is the actual access control here, the same
way a password-reset-token lookup isn't tenant-scoped either.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c3a5e7f9b1d2'
down_revision: Union[str, Sequence[str], None] = 'b2f4c6a1d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION resolve_portal_token(p_token text)
        RETURNS TABLE(instance_id uuid, organization_id uuid)
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT id, organization_id FROM onboarding_instances WHERE portal_token = p_token;
        $$;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION resolve_portal_token(text) TO onboarding_app;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS resolve_portal_token(text);")
