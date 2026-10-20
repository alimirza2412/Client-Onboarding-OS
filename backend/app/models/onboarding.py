import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.database.base import Base
from app.models.enums import OnboardingInstanceStatus, WorkflowExecutionStatus
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OnboardingTemplate(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Minimal template: names which form to use for intake and which
    documents to request. Full per-vertical template configuration is
    deferred beyond the demo — see docs/decisions.md.
    """

    __tablename__ = "onboarding_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("forms.id", ondelete="SET NULL"), nullable=True
    )
    required_documents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_default: Mapped[bool] = mapped_column(default=True)


class OnboardingInstance(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_instances"

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding_templates.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[OnboardingInstanceStatus] = mapped_column(
        SAEnum(OnboardingInstanceStatus, name="onboarding_instance_status"),
        nullable=False,
        default=OnboardingInstanceStatus.NOT_STARTED,
    )
    current_step: Mapped[str] = mapped_column(String(255), nullable=False, default="created")
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Client portal access (Phase 5). A full parallel client-login system
    # (separate from staff JWT auth) is out of scope for a 2-day demo —
    # this is a magic-link-style opaque token instead. See CHANGELOG.md
    # and docs/decisions.md.
    portal_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=lambda: uuid.uuid4().hex
    )

    # Time-to-Start KPI (docs/research.md): Contract/Client Accepted -> Delivery Ready.
    # started_at is set the moment the onboarding instance is created (our proxy for
    # "client accepted"); completed_at is set when the workflow reaches ONBOARDING COMPLETE.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    kickoff_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # AI-generated kickoff brief (Phase 10/12). Free-form JSON — drafted by AI,
    # never authoritative over workflow state (docs/architecture.md).
    kickoff_brief: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    intake_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI Intake Analysis (new). Same pattern as kickoff_brief above: a
    # snapshot dict, drafted by AI, computed once right after intake
    # submission. Never authoritative over workflow state.
    ai_intake_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Missing-information snapshot (new) — deterministic, NOT AI-derived
    # (see app/services/missing_info.py). This column stores the
    # point-in-time result computed right after intake submission, for
    # audit/record purposes. API responses recompute this live instead
    # of reading this column directly, since documents/OAuth connections
    # keep changing after intake — see app/services/missing_info.py's
    # compute_current_missing_info().
    missing_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    client: Mapped["Client"] = relationship()  # noqa: F821
    document_requests: Mapped[list["DocumentRequest"]] = relationship(  # noqa: F821
        order_by="DocumentRequest.created_at",
        primaryjoin="OnboardingInstance.id == foreign(DocumentRequest.onboarding_instance_id)",
        viewonly=True,
    )
    integration_accounts: Mapped[list["IntegrationAccount"]] = relationship(  # noqa: F821
        primaryjoin="OnboardingInstance.id == foreign(IntegrationAccount.onboarding_instance_id)",
        viewonly=True,
    )


class WorkflowExecution(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """
    Audit record of a Temporal workflow run — NOT an execution graph.
    Per decision B1, workflows are code-defined Temporal workflows; this
    table exists purely so the admin dashboard can show workflow status
    without querying Temporal directly.
    """

    __tablename__ = "workflow_executions"

    onboarding_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    temporal_workflow_id: Mapped[str] = mapped_column(String(255), nullable=False)
    temporal_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WorkflowExecutionStatus] = mapped_column(
        SAEnum(WorkflowExecutionStatus, name="workflow_execution_status"),
        nullable=False,
        default=WorkflowExecutionStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
