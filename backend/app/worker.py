"""
Temporal worker entrypoint.

Run this as its own long-running process (in addition to the FastAPI API
and the Next.js frontend) — see DEMO_SETUP.md:

    .venv/bin/python -m app.worker

It connects to the Temporal server, and executes OnboardingWorkflow
instances plus their activities as they're started/signaled by the API.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.config.settings import get_settings
from app.workflows import activities
from app.workflows.onboarding import OnboardingWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onboarding-worker")


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[OnboardingWorkflow],
        activities=[
            activities.update_instance_step,
            activities.analyze_intake_and_detect_missing,
            activities.send_welcome_email,
            activities.send_reminder_email,
            activities.process_documents_ai,
            activities.schedule_kickoff,
            activities.generate_kickoff_brief,
            activities.mark_complete,
            activities.complete_workflow_execution_record,
        ],
    )

    logger.info(
        "Worker starting: address=%s namespace=%s task_queue=%s",
        settings.temporal_address,
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
