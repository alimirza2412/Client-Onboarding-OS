"""
Tests for Task 1 (AI Intake Analysis) + Task 2 (Missing Information
Detection) + Task 6 (Temporal integration).

The pure-logic tests (missing-info detection, AI mock fallback) need no
infrastructure beyond Postgres. The end-to-end test additionally needs
Temporal + a running worker (`python -m app.worker`) — same requirement
DEMO_SETUP.md already documents for exercising the onboarding workflow.
"""

import time
import uuid
from unittest.mock import patch

import httpx
import pytest

from app.services.ai import analyze_intake
from app.services.missing_info import detect_missing_information


class _FakeDocRequest:
    def __init__(self, name: str, has_document: bool):
        self.name = name
        self.documents = [object()] if has_document else []


# --- Task 2: pure, deterministic missing-info logic (no DB, no network) ---


def test_missing_info_detects_incomplete_required_fields():
    """Mirrors the exact example from the task spec."""
    form_definition = {
        "fields": [
            {"key": "company_name", "label": "Company name", "type": "text", "required": True},
            {"key": "website", "label": "Website", "type": "text", "required": True},
            {"key": "budget", "label": "Monthly budget", "type": "number", "required": True},
            {"key": "audience", "label": "Target audience", "type": "text", "required": True},
        ]
    }
    answers = {"company_name": "Acme", "website": "acme.com"}

    result = detect_missing_information(form_definition, answers, [])

    assert result.missing_fields == ["Monthly budget", "Target audience"]
    assert result.completed_fields == ["Company name", "Website"]


def test_missing_info_respects_conditional_show_if():
    """A field hidden by show_if isn't actually required unless its condition is met."""
    form_definition = {
        "fields": [
            {"key": "service", "label": "Service", "type": "select", "required": True},
            {
                "key": "ad_budget",
                "label": "Ad budget",
                "type": "number",
                "required": True,
                "show_if": {"field": "service", "equals": "Paid Ads"},
            },
        ]
    }
    answers = {"service": "SEO"}  # condition not met — ad_budget should not count as missing

    result = detect_missing_information(form_definition, answers, [])
    assert "Ad budget" not in result.missing_fields


def test_missing_info_detects_missing_documents():
    reqs = [_FakeDocRequest("Brand Guidelines", has_document=False), _FakeDocRequest("W9 Form", has_document=True)]
    result = detect_missing_information({"fields": []}, {}, reqs)
    assert result.missing_documents == ["Brand Guidelines"]
    assert result.completed_documents == ["W9 Form"]


def test_missing_info_100_percent_when_everything_present():
    form_definition = {"fields": [{"key": "a", "label": "A", "type": "text", "required": True}]}
    reqs = [_FakeDocRequest("Doc", has_document=True)]
    result = detect_missing_information(form_definition, {"a": "x"}, reqs)
    assert result.progress_percent == 100
    assert result.missing_fields == []
    assert result.missing_documents == []


def test_missing_info_never_uses_ai():
    """Task 2: 'DO NOT use Groq to decide whether a required field is missing.'
    Verified structurally: the module doesn't actually import the AI
    service (checked via AST, not string search, since the module's own
    docstring explains this in prose)."""
    import ast
    import inspect

    import app.services.missing_info as module

    tree = ast.parse(inspect.getsource(module))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)

    assert "app.services.ai" not in imported_modules
    assert not hasattr(module, "analyze_intake")
    assert not hasattr(module, "extract_document_data")


# --- Task 1: AI analysis fallback behavior (no live Groq key needed) ---


def test_ai_intake_analysis_uses_mock_without_api_key():
    result, source = analyze_intake({"company_name": "Test Co", "service": "SEO"})
    assert source == "mock"
    assert "Test Co" in result.client_overview


def test_ai_intake_analysis_falls_back_on_invalid_groq_json():
    """Task 7 test #7: Groq returns invalid/unexpected output -> graceful fallback."""
    import app.services.ai as ai_module

    class BadResponse:
        def raise_for_status(self):
            pass

        def json(self):
            # client_overview empty -> fails IntakeAnalysisResult validation
            return {"choices": [{"message": {"content": '{"client_overview": ""}'}}]}

    original_key = ai_module.settings.groq_api_key
    ai_module.settings.groq_api_key = "fake-key-for-test"
    try:
        with patch.object(httpx, "post", return_value=BadResponse()):
            result, source = analyze_intake({"company_name": "Test Co"})
        assert source == "mock"
    finally:
        ai_module.settings.groq_api_key = original_key


def test_ai_intake_analysis_falls_back_on_network_error():
    """Task 7 test: Groq API key exists but the call fails -> graceful fallback."""
    import app.services.ai as ai_module

    original_key = ai_module.settings.groq_api_key
    ai_module.settings.groq_api_key = "fake-key-for-test"
    try:
        with patch.object(httpx, "post", side_effect=httpx.ConnectError("boom")):
            result, source = analyze_intake({"company_name": "Test Co"})
        assert source == "mock"
    finally:
        ai_module.settings.groq_api_key = original_key


def test_ai_intake_analysis_uses_groq_when_response_is_valid():
    import app.services.ai as ai_module

    class GoodResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"client_overview": "A great client.", "goals": ["Grow"], '
                                '"requested_services": ["SEO"], "key_requirements": [], '
                                '"important_details": [], "potential_concerns": []}'
                            )
                        }
                    }
                ]
            }

    original_key = ai_module.settings.groq_api_key
    ai_module.settings.groq_api_key = "fake-key-for-test"
    try:
        with patch.object(httpx, "post", return_value=GoodResponse()):
            result, source = analyze_intake({"company_name": "Test Co"})
        assert source == "groq"
        assert result.client_overview == "A great client."
    finally:
        ai_module.settings.groq_api_key = original_key


# --- End-to-end: real API + real Temporal workflow ---


BASE_URL = "http://127.0.0.1:8000"


def _temporal_available() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _temporal_available(), reason="API server not reachable")
def test_ai_analysis_integrates_with_real_onboarding_workflow(registered_org):
    """
    Task 7, full integration: submits an incomplete intake through the
    real portal API, backed by a real Temporal workflow, and verifies:
      - the AI analysis + missing-info are correctly associated with
        THIS instance (not leaked from/to another)
      - staff sees the AI summary
      - the client portal sees only actionable missing items, no AI analysis
      - the workflow keeps running afterward (doesn't break — Task 6)
    """
    client, _ = registered_org

    r = client.post(
        "/forms",
        json={
            "name": "AI Test Form",
            "definition": {
                "fields": [
                    {"key": "company_name", "label": "Company name", "type": "text", "required": True},
                    {"key": "service", "label": "Service", "type": "text", "required": True},
                ]
            },
        },
    )
    form_id = r.json()["id"]

    r = client.post(
        "/templates",
        json={"name": "AI Test Template", "form_id": form_id, "required_documents": ["W9 Form"]},
    )
    template_id = r.json()["id"]

    r = client.post(
        "/clients",
        json={"name": "AI Test Client", "contact": {"name": "C", "email": "aitest@example-agency.io"}},
    )
    client_id = r.json()["id"]

    r = client.post("/onboarding-instances", json={"client_id": client_id, "template_id": template_id})
    assert r.status_code == 201
    instance_id = r.json()["id"]

    r = client.get(f"/onboarding-instances/{instance_id}/portal-link")
    portal_token = r.json()["portal_path"].split("/")[-1]
    portal = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # Submit INCOMPLETE intake (missing "service") — no document uploaded either
    r = portal.post(f"/portal/{portal_token}/intake", json={"answers": {"company_name": "AI Test Client"}})
    assert r.status_code == 204

    # Give the Temporal activity a moment to run
    time.sleep(3)

    # Staff sees the AI summary and correct missing info, scoped to this instance
    r = client.get(f"/onboarding-instances/{instance_id}")
    assert r.status_code == 200
    staff_data = r.json()
    assert staff_data["ai_intake_analysis"] is not None
    assert "AI Test Client" in staff_data["ai_intake_analysis"]["client_overview"]
    assert "Service" in staff_data["missing_info"]["missing_fields"]
    assert "W9 Form" in staff_data["missing_info"]["missing_documents"]

    # Client portal sees only actionable items — no AI analysis exposed
    r = portal.get(f"/portal/{portal_token}")
    assert r.status_code == 200
    portal_data = r.json()
    assert "ai_intake_analysis" not in portal_data
    assert portal_data["missing_info"]["missing_fields"] == ["Service"]
    assert portal_data["missing_info"]["missing_documents"] == ["W9 Form"]
    assert portal_data["missing_info"]["progress_percent"] < 100
    assert portal_data["missing_info"]["next_action"] == "Complete the missing information."

    # Workflow is still alive and queryable — AI analysis didn't break anything
    r = client.get(f"/onboarding-instances/{instance_id}/workflow-status")
    assert r.status_code == 200
    assert r.json()["queryable"] is True
