import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def registered_org(client: TestClient):
    """
    Registers a brand-new organization + OWNER user with unique random
    data, and returns (client_with_auth_header, org_info). Tests don't
    share fixtures across a persistent test DB, so uniqueness avoids
    collisions between runs — see DEMO_SETUP.md for why tests run
    against a real local Postgres rather than an isolated test DB.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"owner-{suffix}@example-agency.io"
    password = "test-password-123"
    org_name = f"Test Agency {suffix}"

    r = client.post(
        "/auth/register",
        json={
            "organization_name": org_name,
            "full_name": "Test Owner",
            "email": email,
            "password": password,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    return client, {"email": email, "password": password, "org_name": org_name}
