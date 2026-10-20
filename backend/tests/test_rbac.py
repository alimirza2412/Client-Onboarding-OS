import uuid as uuid_module

from app.database.session import SessionLocal, set_tenant_context
from app.models.enums import MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.utils.security import create_access_token, hash_password


def _add_member_with_role(org_id, email: str, role: MemberRole) -> str:
    """
    Directly inserts a user + membership with a given role (no invite
    endpoint exists yet — see CHANGELOG.md) and returns a bearer token
    for them.
    """
    db = SessionLocal()
    try:
        set_tenant_context(db, org_id)
        user = User(email=email, full_name="Role Test User", hashed_password=hash_password("x"))
        db.add(user)
        db.flush()
        db.add(OrganizationMember(organization_id=org_id, user_id=user.id, role=role))
        db.commit()
        return create_access_token(str(user.id))
    finally:
        db.close()


def test_client_role_cannot_access_admin_functions(registered_org):
    owner_client, info = registered_org
    r = owner_client.get("/auth/me")
    org_id = r.json()["memberships"][0]["organization_id"]

    token = _add_member_with_role(org_id, f"rbac-client-role-{uuid_module.uuid4().hex[:8]}@example-agency.io", MemberRole.CLIENT)

    from fastapi.testclient import TestClient
    from app.main import app

    client_role_session = TestClient(app)
    client_role_session.headers["Authorization"] = f"Bearer {token}"

    # STAFF-or-above endpoint
    r = client_role_session.get("/clients")
    assert r.status_code == 403

    # ADMIN-or-above endpoint
    r = client_role_session.post("/forms", json={"name": "x", "definition": {"fields": []}})
    assert r.status_code == 403


def test_staff_role_can_manage_clients_but_not_forms(registered_org):
    owner_client, info = registered_org
    r = owner_client.get("/auth/me")
    org_id = r.json()["memberships"][0]["organization_id"]

    token = _add_member_with_role(org_id, f"rbac-staff-role-{uuid_module.uuid4().hex[:8]}@example-agency.io", MemberRole.STAFF)

    from fastapi.testclient import TestClient
    from app.main import app

    staff_session = TestClient(app)
    staff_session.headers["Authorization"] = f"Bearer {token}"

    # STAFF can manage clients
    r = staff_session.post(
        "/clients",
        json={"name": "Staff-created client", "contact": {"name": "C", "email": "c@example-agency.io"}},
    )
    assert r.status_code == 201

    # STAFF cannot create forms (ADMIN-or-above only)
    r = staff_session.post("/forms", json={"name": "x", "definition": {"fields": []}})
    assert r.status_code == 403


def test_admin_role_can_manage_forms(registered_org):
    owner_client, info = registered_org
    r = owner_client.get("/auth/me")
    org_id = r.json()["memberships"][0]["organization_id"]

    token = _add_member_with_role(org_id, f"rbac-admin-role-{uuid_module.uuid4().hex[:8]}@example-agency.io", MemberRole.ADMIN)

    from fastapi.testclient import TestClient
    from app.main import app

    admin_session = TestClient(app)
    admin_session.headers["Authorization"] = f"Bearer {token}"

    r = admin_session.post(
        "/forms", json={"name": "Admin form", "definition": {"fields": [{"key": "a", "label": "A", "type": "text"}]}}
    )
    assert r.status_code == 201


def test_owner_has_full_permissions(registered_org):
    owner_client, _ = registered_org
    r = owner_client.post(
        "/forms", json={"name": "Owner form", "definition": {"fields": [{"key": "a", "label": "A", "type": "text"}]}}
    )
    assert r.status_code == 201
