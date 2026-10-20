"""
Schemas for the AI Intake Analysis feature.

IntakeAnalysisResult is what Groq's response gets validated against
(app/services/ai.py:analyze_intake). MissingInfoResult is the output of
the DETERMINISTIC missing-information check (app/services/missing_info.py)
— it lives in this file because it's returned alongside the AI analysis
in the same API responses, not because it's AI-derived. It is not.
"""

from pydantic import BaseModel, Field, field_validator


def _as_string_list(value: object) -> list[str]:
    """Groq sometimes returns a bare string instead of a one-item list —
    coerce rather than fail validation outright (Task 7: 'Groq returns
    invalid/unexpected output' should degrade gracefully, not crash)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)]


class IntakeAnalysisResult(BaseModel):
    """
    Structured result of AI Intake Analysis (Task 1). Drafted by AI —
    advisory only, never authoritative over onboarding state
    (docs/architecture.md).
    """

    client_overview: str = Field(min_length=1, max_length=1000)
    goals: list[str] = Field(default_factory=list)
    requested_services: list[str] = Field(default_factory=list)
    key_requirements: list[str] = Field(default_factory=list)
    important_details: list[str] = Field(default_factory=list)
    potential_concerns: list[str] = Field(default_factory=list)

    @field_validator(
        "goals",
        "requested_services",
        "key_requirements",
        "important_details",
        "potential_concerns",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: object) -> list[str]:
        return _as_string_list(value)

    @field_validator("client_overview", mode="before")
    @classmethod
    def _coerce_overview(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("client_overview must not be empty")
        return str(value)


class MissingInfoResult(BaseModel):
    """
    Deterministic (NOT AI) comparison of what a form/template requires
    against what's actually been submitted/uploaded. See
    app/services/missing_info.py — Groq is never involved in this.
    """

    missing_fields: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    completed_fields: list[str] = Field(default_factory=list)
    completed_documents: list[str] = Field(default_factory=list)
    progress_percent: int = Field(ge=0, le=100, default=100)
