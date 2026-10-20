"""
Import every model module here so they all register on Base.metadata —
required for Alembic autogenerate and for `Base.metadata.create_all()` in
tests to see the full schema.
"""

from app.models.audit import AuditLog, EmailLog
from app.models.client import Client, Contact
from app.models.document import Document, DocumentRequest
from app.models.integration import IntegrationAccount
from app.models.onboarding import OnboardingInstance, OnboardingTemplate, WorkflowExecution
from app.models.organization import Organization, OrganizationMember
from app.models.form import Form, FormSubmission, FormVersion
from app.models.user import User

__all__ = [
    "AuditLog",
    "EmailLog",
    "Client",
    "Contact",
    "Document",
    "DocumentRequest",
    "IntegrationAccount",
    "OnboardingInstance",
    "OnboardingTemplate",
    "WorkflowExecution",
    "Organization",
    "OrganizationMember",
    "Form",
    "FormSubmission",
    "FormVersion",
    "User",
]
