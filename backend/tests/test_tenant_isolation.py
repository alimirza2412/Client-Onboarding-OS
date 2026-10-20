import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register(email_prefix: str) -> tuple[TestClient, str]:
    c = TestClient(app)
    suffix = uuid.uuid4().hex[:8]
    r = c.post(
        "/auth/register",
        json={
            "organization_name": f"Org {suffix}",
            "full_name": "Owner",
            "email": f"{email_prefix}-{suffix}@example-agency.io",
            "password": "test-password-123",
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c, token


def test_organization_a_cannot_see_organization_b_clients():
    """
    Phase 1's critical test: 'Organization A must never access
    Organization B data.' Exercised end-to-end through the real API —
    both the application-level organization_id filter AND PostgreSQL RLS
    (decision D2) are in play here, not mocked.
    """
    client_a, _ = _register("org-a-owner")
    client_b, _ = _register("org-b-owner")

    r = client_a.post(
        "/clients",
        json={"name": "Org A's Secret Client", "contact": {"name": "A Contact", "email": "a@example-agency.io"}},
    )
    assert r.status_code == 201
    client_a_client_id = r.json()["id"]

    # Org B should see NO clients at all (it hasn't created any, and must
    # not see Org A's)
    r = client_b.get("/clients")
    assert r.status_code == 200
    assert r.json() == []

    # Org B directly requesting Org A's client by ID must 404, not 200
    r = client_b.get(f"/clients/{client_a_client_id}")
    assert r.status_code == 404

    # Org A can see its own client just fine
    r = client_a.get("/clients")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == client_a_client_id
