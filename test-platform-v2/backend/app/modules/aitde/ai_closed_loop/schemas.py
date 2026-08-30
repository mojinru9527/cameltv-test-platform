"""AITDE V3.8 AI QA Closed Loop API schemas (V38)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TriageIn(BaseModel):
    """Run failure triage. Context is optional; the run is always the subject."""

    context: dict = Field(default_factory=dict)
    model_ref: str | None = None
    prompt_version: str | None = None


class HypothesisReviewIn(BaseModel):
    """Confirm / reject a FailureHypothesis (V38-003 audit)."""

    status: str = Field("REVIEWED", description="REVIEWED | CONFIRMED | REJECTED")
    reviewed_by: int | None = None
    reason: str | None = None


class HealingApplyIn(BaseModel):
    """Apply an approved Action-only healing proposal (V38-005)."""

    approved_by: int | None = None
    note: str | None = None


class SuggestionReviewIn(BaseModel):
    """Review an AI suggestion (V38-011 Inbox)."""

    status: str = Field("APPROVED", description="APPROVED | REJECTED")
    reviewed_by: int | None = None
    reason: str | None = None


class GapConvertIn(BaseModel):
    """Convert a Scenario Gap proposal into a Contract/Scenario change proposal."""

    title: str | None = None
    risk_level: str = "P2"
    description: str | None = None


class FeedbackIn(BaseModel):
    """Append-only Tester feedback (V38-012)."""

    project_id: int = 0
    mission_id: int | None = None
    target_type: str = ""
    target_id: int = 0
    feedback_type: str = "CORRECTION"
    before: dict | None = None
    after: dict | None = None
    reason: str | None = None
    created_by: int = 0


class ModelEvaluationIn(BaseModel):
    """Record a golden model/prompt evaluation run (V38-013)."""

    evaluation_suite: str
    model_ref: str
    prompt_versions: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    status: str = "COMPLETED"
    artifact_uri: str | None = None
