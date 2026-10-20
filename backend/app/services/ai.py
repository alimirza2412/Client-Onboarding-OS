"""
AI document extraction (Phase 10).

Uses Groq's chat completions API directly over HTTP (avoids adding a
whole SDK dependency for one call — "keep it simple" per the demo
scope). If GROQ_API_KEY isn't set, falls back to a deterministic mock
extraction so the demo works end-to-end without a live API key.

Per docs/architecture.md: AI assists extraction/summarization but never
directly controls workflow state — callers always gate on the returned
confidence score and route low-confidence results to human review
(see app/workflows/onboarding.py activities).
"""

import hashlib
import json
import random

import httpx

from app.config.settings import get_settings
from app.schemas.ai import IntakeAnalysisResult

settings = get_settings()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

EXTRACTION_PROMPT = """You extract structured business information from a document's text \
for a marketing agency's client-onboarding system. Given the raw text below, return ONLY a \
JSON object (no prose, no markdown fences) with these keys: \
company_name (string or null), document_type (string guess, e.g. "invoice", "brand guideline", \
"contract", "other"), key_facts (array of up to 5 short strings summarizing important details).

TEXT:
{text}
"""

# Dedicated prompt for Task 1 (AI Intake Analysis) — deliberately NOT the
# same prompt as document extraction above; different input shape
# (structured form answers, not raw document text) and different output
# shape (business analysis, not document classification).
INTAKE_ANALYSIS_PROMPT = """You are analyzing a new client's intake form submission for a \
marketing agency's client-onboarding system. Given the submitted answers below (as JSON), \
produce a concise structured analysis for the agency's staff. Return ONLY a JSON object \
(no prose, no markdown fences) with exactly these keys:

client_overview: a 1-2 sentence plain-English summary of who this client is.
goals: array of short strings — what the client wants to achieve.
requested_services: array of short strings — services they're asking for.
key_requirements: array of short strings — concrete requirements or constraints they mentioned.
important_details: array of short strings — anything else worth flagging to the team.
potential_concerns: array of short strings — risks, ambiguities, or red flags; empty array if none.

INTAKE ANSWERS (JSON):
{answers_json}
"""


def _mock_extract(text: str) -> tuple[dict, float]:
    """Deterministic, seeded mock so demo runs are reproducible."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    words = [w.strip(".,") for w in text.split() if len(w) > 3][:5]
    data = {
        "company_name": (words[0].title() if words else "Unknown"),
        "document_type": rng.choice(["invoice", "brand guideline", "contract", "other"]),
        "key_facts": [f"Mentions '{w}'" for w in words] or ["No extractable content found"],
    }
    # Deliberately vary confidence so the demo exercises both the
    # auto-approve and human-review paths (Phase 10 requirement).
    confidence = round(rng.uniform(0.55, 0.98), 2)
    return data, confidence


def extract_document_data(text: str) -> tuple[dict, float]:
    """
    Returns (extracted_data, confidence). Never raises — falls back to
    the mock extractor on any error so a flaky/missing AI provider can
    never block the onboarding workflow (architecture requirement: AI
    assists but never owns critical state).
    """
    if not settings.groq_api_key:
        return _mock_extract(text)

    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:4000])}
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        # Groq doesn't return a confidence score itself; derive a simple
        # proxy from whether it found a company name (kept intentionally
        # simple for the demo — see CHANGELOG.md).
        confidence = 0.9 if data.get("company_name") else 0.6
        return data, confidence
    except Exception:
        return _mock_extract(text)


def _mock_intake_analysis(answers: dict) -> IntakeAnalysisResult:
    """
    Deterministic fallback used when GROQ_API_KEY is unset, or when the
    live call fails/returns something that doesn't validate (Task 1: the
    app must keep working either way). Built directly from the actual
    submitted answers — not a generic word-guessing mock — so it's still
    a reasonably sensible demo response, clearly labeled as a fallback
    via the "generated_by" field the caller attaches (see
    app/workflows/activities.py:analyze_intake_and_detect_missing).
    """
    company = answers.get("company_name") or answers.get("company") or "This client"
    service = answers.get("service") or answers.get("requested_services")
    service_str = service if isinstance(service, str) else ", ".join(service) if service else None

    other_details = [
        f"{k.replace('_', ' ')}: {v}"
        for k, v in answers.items()
        if k not in ("company_name", "company", "service", "requested_services") and v not in (None, "", [])
    ]

    return IntakeAnalysisResult(
        client_overview=(
            f"{company} submitted an intake form"
            + (f" requesting {service_str}" if service_str else "")
            + ". (Demo fallback summary — connect GROQ_API_KEY for real AI analysis.)"
        ),
        goals=[f"Grow through {service_str}"] if service_str else [],
        requested_services=[service_str] if service_str else [],
        key_requirements=other_details[:5],
        important_details=["Generated by demo fallback, not live AI — see GROQ_API_KEY in DEMO_SETUP.md."],
        potential_concerns=[] if answers else ["No intake answers were submitted."],
    )


def analyze_intake(answers: dict) -> tuple[IntakeAnalysisResult, str]:
    """
    Task 1 — AI Intake Analysis. Returns (result, source) where source
    is "groq" or "mock", so callers/UI can clearly label which one
    produced it (Task 1: "use a clearly identified fallback/demo
    response").

    Never raises: any failure (no API key, network error, invalid JSON,
    a response that fails IntakeAnalysisResult validation) falls back to
    the deterministic mock instead — AI must not be able to break the
    onboarding workflow.
    """
    if not settings.groq_api_key:
        return _mock_intake_analysis(answers), "mock"

    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [
                    {
                        "role": "user",
                        "content": INTAKE_ANALYSIS_PROMPT.format(
                            answers_json=json.dumps(answers, default=str)[:4000]
                        ),
                    }
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        # Pydantic validation (Task 1: "Use Pydantic validation for the
        # AI response") — if Groq returned something malformed, this
        # raises and we fall through to the mock below.
        result = IntakeAnalysisResult(**data)
        return result, "groq"
    except Exception:
        return _mock_intake_analysis(answers), "mock"
