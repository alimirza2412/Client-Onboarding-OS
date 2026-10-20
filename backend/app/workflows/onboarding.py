"""
The main onboarding workflow (Phase 7 / Phase 12).

Per decision B1 (docs/decisions.md), this is a plain code-defined
Temporal workflow — no visual/graph-based workflow builder. It
orchestrates the flow from docs/architecture.md's "Main onboarding
workflow" diagram:

    Create Onboarding -> Welcome Email -> Dynamic Intake ->
    Document Collection -> AI Extraction -> OAuth Connections ->
    Schedule Kickoff -> Generate AI Kickoff Brief -> ONBOARDING COMPLETE

Human wait states (waiting for the client to submit the form, upload
documents, connect accounts) are implemented with Temporal signals +
`workflow.wait_condition` — the workflow can wait indefinitely (hours,
days) without holding a worker thread, and survives worker restarts
(Phase 7's critical test — see DEMO_SETUP.md for how to verify this).

All actual I/O happens in activities.py; this file only orchestrates.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflows import activities


DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_attempts=3,
)


@dataclass
class OnboardingWorkflowInput:
    instance_id: str
    organization_id: str
    client_name: str
    client_email: str
    required_document_names: list[str] = field(default_factory=list)
    required_providers: list[str] = field(default_factory=lambda: ["GOOGLE", "META"])
    # Demo-only: stand-in for the real 24h/48h/72h reminder cadence in
    # docs/research.md, so a live demo can actually observe a reminder
    # fire without waiting real hours. See DEMO_SETUP.md.
    reminder_delay_seconds: int = 90


@workflow.defn
class OnboardingWorkflow:
    def __init__(self) -> None:
        self._form_submitted = False
        self._uploaded_document_ids: set[str] = set()
        self._connected_providers: set[str] = set()

    # --- Signals: fired by the API when a client takes an action ---

    @workflow.signal
    def submit_intake_form(self) -> None:
        self._form_submitted = True

    @workflow.signal
    def upload_document(self, document_id: str) -> None:
        self._uploaded_document_ids.add(document_id)

    @workflow.signal
    def connect_oauth(self, provider: str) -> None:
        self._connected_providers.add(provider)

    # --- Queries: let the API/tests introspect live workflow state ---

    @workflow.query
    def status(self) -> dict:
        return {
            "form_submitted": self._form_submitted,
            "documents_uploaded": len(self._uploaded_document_ids),
            "connected_providers": sorted(self._connected_providers),
        }

    @workflow.run
    async def run(self, input: OnboardingWorkflowInput) -> dict:
        await workflow.execute_activity(
            activities.send_welcome_email,
            args=[input.instance_id, input.organization_id, input.client_name, input.client_email],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # --- Wait for intake form, with a demo reminder if it's slow ---
        await workflow.execute_activity(
            activities.update_instance_step,
            args=[input.instance_id, input.organization_id, "awaiting_intake_form"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        try:
            await workflow.wait_condition(
                lambda: self._form_submitted,
                timeout=timedelta(seconds=input.reminder_delay_seconds),
            )
        except TimeoutError:
            await workflow.execute_activity(
                activities.update_instance_step,
                args=[input.instance_id, input.organization_id, "blocked_awaiting_intake_form", "BLOCKED"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.execute_activity(
                activities.send_reminder_email,
                args=[
                    input.instance_id,
                    input.organization_id,
                    input.client_name,
                    input.client_email,
                    "intake form",
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            await workflow.wait_condition(lambda: self._form_submitted)
            await workflow.execute_activity(
                activities.update_instance_step,
                args=[input.instance_id, input.organization_id, "intake_form_submitted", "IN_PROGRESS"],
                start_to_close_timeout=timedelta(seconds=30),
            )

        # --- AI Intake Analysis + Missing Information Detection (new) ---
        # Runs once, right after the intake form is submitted (whichever
        # path above got us here), before document collection starts.
        await workflow.execute_activity(
            activities.update_instance_step,
            args=[input.instance_id, input.organization_id, "analyzing_intake"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            activities.analyze_intake_and_detect_missing,
            args=[input.instance_id, input.organization_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # --- Wait for all requested documents ---
        required_doc_count = len(input.required_document_names)
        if required_doc_count > 0:
            await workflow.execute_activity(
                activities.update_instance_step,
                args=[input.instance_id, input.organization_id, "awaiting_documents"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.wait_condition(
                lambda: len(self._uploaded_document_ids) >= required_doc_count
            )
            await workflow.execute_activity(
                activities.update_instance_step,
                args=[input.instance_id, input.organization_id, "processing_documents"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.execute_activity(
                activities.process_documents_ai,
                args=[input.instance_id, input.organization_id],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        # --- Wait for OAuth connections ---
        if input.required_providers:
            await workflow.execute_activity(
                activities.update_instance_step,
                args=[input.instance_id, input.organization_id, "awaiting_oauth_connections"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.wait_condition(
                lambda: set(input.required_providers) <= self._connected_providers
            )

        # --- Kickoff scheduling + AI brief ---
        await workflow.execute_activity(
            activities.update_instance_step,
            args=[input.instance_id, input.organization_id, "scheduling_kickoff"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            activities.schedule_kickoff,
            args=[input.instance_id, input.organization_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        await workflow.execute_activity(
            activities.generate_kickoff_brief,
            args=[input.instance_id, input.organization_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # --- Complete ---
        await workflow.execute_activity(
            activities.mark_complete,
            args=[input.instance_id, input.organization_id, input.client_name, input.client_email],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        await workflow.execute_activity(
            activities.complete_workflow_execution_record,
            args=[input.instance_id, input.organization_id],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return self.status()
