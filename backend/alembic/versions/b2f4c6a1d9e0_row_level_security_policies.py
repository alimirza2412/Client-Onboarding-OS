"""row level security policies

Revises: e33c1ca82e64

Implements decision D2 (docs/decisions.md): PostgreSQL Row-Level Security
as a backstop layer on top of application-level organization_id filtering.
See docs/decisions.md and app/database/session.py for the full rationale.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b2f4c6a1d9e0'
down_revision: Union[str, Sequence[str], None] = 'e33c1ca82e64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = [
    "audit_logs",
    "clients",
    "forms",
    "organization_members",
    "contacts",
    "form_versions",
    "onboarding_templates",
    "onboarding_instances",
    "document_requests",
    "email_log",
    "form_submissions",
    "integration_accounts",
    "workflow_executions",
    "documents",
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (organization_id = current_setting('app.current_org_id', true)::uuid)
            WITH CHECK (organization_id = current_setting('app.current_org_id', true)::uuid);
            """
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
