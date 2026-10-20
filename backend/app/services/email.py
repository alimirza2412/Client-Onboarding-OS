"""
EmailProvider abstraction (Phase 8).

For the demo, "sending" an email means logging it to the email_log table
and printing it, instead of calling a real provider (Resend/Postmark per
docs/research.md). Swapping in a real provider later means implementing
this same interface — nothing else in the codebase would need to change.
"""

import abc
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import EmailLog


class EmailProvider(abc.ABC):
    @abc.abstractmethod
    def send(
        self,
        db: Session,
        organization_id: uuid.UUID,
        to_address: str,
        subject: str,
        body: str,
        onboarding_instance_id: uuid.UUID | None = None,
    ) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    """Logs to stdout + the email_log table. No real email is sent."""

    def send(
        self,
        db: Session,
        organization_id: uuid.UUID,
        to_address: str,
        subject: str,
        body: str,
        onboarding_instance_id: uuid.UUID | None = None,
    ) -> None:
        print(f"[email-mock] to={to_address} subject={subject!r}")
        entry = EmailLog(
            organization_id=organization_id,
            onboarding_instance_id=onboarding_instance_id,
            to_address=to_address,
            subject=subject,
            body=body,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()


email_provider: EmailProvider = ConsoleEmailProvider()


# --- Simple templates (Phase 8) ---

def welcome_email_body(client_name: str) -> str:
    return (
        f"Hi {client_name},\n\n"
        f"Welcome aboard! We've created your onboarding portal — please log in "
        f"to complete your intake form and upload any requested documents.\n\n"
        f"— Your Agency Team"
    )


def kickoff_reminder_body(client_name: str) -> str:
    return (
        f"Hi {client_name},\n\n"
        f"Your onboarding is almost complete. We'll be in touch shortly to "
        f"schedule your kickoff call.\n\n"
        f"— Your Agency Team"
    )


def onboarding_complete_body(client_name: str) -> str:
    return (
        f"Hi {client_name},\n\n"
        f"Your onboarding is complete and your project is now underway. "
        f"Welcome to the team!\n\n"
        f"— Your Agency Team"
    )
