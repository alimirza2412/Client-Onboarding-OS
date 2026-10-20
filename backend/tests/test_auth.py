import uuid


def test_register_creates_org_and_returns_token(client):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/register",
        json={
            "organization_name": f"Fresh Co {suffix}",
            "full_name": "New Owner",
            "email": f"fresh-owner-{suffix}@example-agency.io",
            "password": "test-password-123",
        },
    )
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_duplicate_email_registration_rejected(client):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "organization_name": f"Dup Co {suffix}",
        "full_name": "Dup Owner",
        "email": f"dup-owner-{suffix}@example-agency.io",
        "password": "test-password-123",
    }
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409


def test_login_with_wrong_password_rejected(client, registered_org):
    _, info = registered_org
    r = client.post("/auth/login", json={"email": info["email"], "password": "wrong-password"})
    assert r.status_code == 401


def test_me_returns_membership(registered_org):
    client, info = registered_org
    r = client.get("/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == info["email"]
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role"] == "OWNER"
    assert body["memberships"][0]["organization_name"] == info["org_name"]


def test_unauthenticated_request_rejected(client):
    r = client.get("/clients")
    assert r.status_code == 401
