"""
Seeds demo data AND walks the full onboarding flow end-to-end through
real HTTP calls to the running API — exercising FastAPI, PostgreSQL
(with RLS), and the live Temporal workflow together, the same way the
frontend would.

Run with the API server, worker, Postgres, and Temporal all running
(see DEMO_SETUP.md):

    .venv/bin/python scripts/seed_demo.py
"""

import sys
import tempfile
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
DEMO_EMAIL = "owner@demoagency.io"
DEMO_PASSWORD = "demo-password-123"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    step("Health check")
    r = client.get("/health")
    r.raise_for_status()
    print(r.json())

    step("Register (or log in if already seeded)")
    r = client.post(
        "/auth/register",
        json={
            "organization_name": "Demo Marketing Agency",
            "full_name": "Demo Owner",
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
        },
    )
    if r.status_code == 409:
        print("Already registered, logging in instead")
        r = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    r.raise_for_status()
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print("Authenticated OK")

    step("Create intake form")
    r = client.post(
        "/forms",
        json={
            "name": "Agency Intake",
            "definition": {
                "fields": [
                    {"key": "company_name", "label": "Company name", "type": "text", "required": True},
                    {
                        "key": "service",
                        "label": "Primary service",
                        "type": "select",
                        "options": ["Paid Ads", "SEO", "Web Dev"],
                        "required": True,
                    },
                    {
                        "key": "ad_budget",
                        "label": "Monthly ad budget",
                        "type": "number",
                        "show_if": {"field": "service", "equals": "Paid Ads"},
                    },
                ]
            },
        },
    )
    r.raise_for_status()
    form = r.json()
    form_id = form["id"]
    print(f"Form id={form_id}, version 1 published={form['versions'][0]['is_published']}")

    step("Create onboarding template")
    r = client.post(
        "/templates",
        json={
            "name": "Standard Agency Onboarding",
            "form_id": form_id,
            "required_documents": ["Brand Guidelines", "W9 Form"],
        },
    )
    r.raise_for_status()
    template = r.json()
    print(f"Template id={template['id']}")

    step("Create client")
    r = client.post(
        "/clients",
        json={
            "name": "Acme Roasters",
            "contact": {"name": "Jamie Lee", "email": "jamie@acmeroasters.io", "is_primary": True},
        },
    )
    r.raise_for_status()
    client_record = r.json()
    client_id = client_record["id"]
    print(f"Client id={client_id}")

    step("Create onboarding instance (starts Temporal workflow)")
    r = client.post(
        "/onboarding-instances",
        json={"client_id": client_id, "template_id": template["id"]},
    )
    r.raise_for_status()
    instance = r.json()
    instance_id = instance["id"]
    print(f"Instance id={instance_id}, status={instance['status']}, step={instance['current_step']}")
    print(f"Temporal workflow_id (visible via `temporal workflow show`): onboarding-{instance_id}")

    step("Get portal link")
    r = client.get(f"/onboarding-instances/{instance_id}/portal-link")
    r.raise_for_status()
    portal_path = r.json()["portal_path"]
    portal_token = portal_path.split("/")[-1]
    print(f"Portal path: {portal_path}")

    # From here on, act as the CLIENT — no auth header, just the token
    portal = httpx.Client(base_url=BASE_URL, timeout=10.0)

    step("Client: view portal status")
    r = portal.get(f"/portal/{portal_token}")
    r.raise_for_status()
    portal_status = r.json()
    print(f"current_step={portal_status['current_step']}, intake_form present={portal_status['intake_form'] is not None}")

    step("Client: submit intake form")
    r = portal.post(
        f"/portal/{portal_token}/intake",
        json={"answers": {"company_name": "Acme Roasters", "service": "Paid Ads", "ad_budget": 5000}},
    )
    r.raise_for_status()
    print("Intake submitted")

    step("Client: upload requested documents")
    r = portal.get(f"/portal/{portal_token}")
    r.raise_for_status()
    doc_requests = r.json()["document_requests"]
    for req in doc_requests:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(f"Sample content for {req['name']} — Acme Roasters, invoice #12345, total $2,500.")
            tmp_path = f.name
        with open(tmp_path, "rb") as fh:
            r = portal.post(
                f"/portal/{portal_token}/documents/{req['id']}/upload",
                files={"file": (f"{req['name']}.txt", fh, "text/plain")},
            )
        r.raise_for_status()
        print(f"Uploaded for '{req['name']}': {r.json()}")
        Path(tmp_path).unlink(missing_ok=True)

    step("Client: connect OAuth accounts (mocked)")
    for provider in ("GOOGLE", "META"):
        r = portal.post(f"/portal/{portal_token}/oauth/connect", json={"provider": provider})
        r.raise_for_status()
        print(f"Connected {provider}: {r.json()}")

    step("Poll until the workflow completes")
    deadline = time.time() + 60
    final_instance = None
    while time.time() < deadline:
        r = client.get(f"/onboarding-instances/{instance_id}")
        r.raise_for_status()
        final_instance = r.json()
        print(f"  status={final_instance['status']} step={final_instance['current_step']}")
        if final_instance["status"] == "COMPLETED":
            break
        time.sleep(2)

    if final_instance is None or final_instance["status"] != "COMPLETED":
        print("\nFAILED: workflow did not reach COMPLETED within timeout.")
        return 1

    step("Final result")
    print("Kickoff brief:", final_instance["kickoff_brief"])
    print("Document review statuses:")
    for req in final_instance["document_requests"]:
        for doc in req["documents"]:
            print(f"  {doc['original_filename']}: confidence={doc['ai_confidence']} review={doc['review_status']}")

    step("Live Temporal workflow query")
    r = client.get(f"/onboarding-instances/{instance_id}/workflow-status")
    r.raise_for_status()
    print(r.json())

    step("Dashboard summary")
    r = client.get("/dashboard/summary")
    r.raise_for_status()
    print(r.json())

    print("\n✅ End-to-end demo flow completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
