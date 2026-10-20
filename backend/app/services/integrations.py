"""
IntegrationProvider abstraction (Phase 9).

Real OAuth (Google/Meta) needs registered OAuth apps and live credentials
that don't exist for a 2-day demo — see docs/decisions.md and
CHANGELOG.md. This mocks the *outcome* of the flow described in
docs/architecture.md:

    Client -> Connect Account -> Provider Authorization -> Callback ->
    Encrypt/store tokens -> Verify API access -> Confirm permissions ->
    CONNECTED

so the rest of the system (workflow wait states, dashboard status, etc.)
behaves exactly as it would with real OAuth wired in later — only the
"Provider Authorization" hop itself is skipped.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import IntegrationProvider, IntegrationStatus
from app.models.integration import IntegrationAccount


def mock_connect(
    db: Session,
    organization_id: uuid.UUID,
    onboarding_instance_id: uuid.UUID,
    provider: IntegrationProvider,
) -> IntegrationAccount:
    """
    Simulates a successful OAuth connection + API verification. In a real
    implementation this would run after the OAuth callback, having
    already stored encrypted tokens and confirmed API access.
    """
    account = (
        db.query(IntegrationAccount)
        .filter(
            IntegrationAccount.onboarding_instance_id == onboarding_instance_id,
            IntegrationAccount.provider == provider,
        )
        .first()
    )
    if account is None:
        account = IntegrationAccount(
            organization_id=organization_id,
            onboarding_instance_id=onboarding_instance_id,
            provider=provider,
        )
        db.add(account)

    account.status = IntegrationStatus.CONNECTED
    account.connected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    return account
