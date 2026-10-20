"""
Shared Temporal client for the API process (separate from the worker
process in app/worker.py — the API starts/signals workflows, the worker
executes them).
"""

from temporalio.client import Client

from app.config.settings import get_settings

_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    return _client
