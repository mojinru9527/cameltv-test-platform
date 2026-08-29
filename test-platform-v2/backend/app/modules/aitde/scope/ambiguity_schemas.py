"""Ambiguity / Intent Pydantic schemas (V30-040..V30-044)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import RiskLevel
from app.modules.aitde.scope.schemas import SourceRef


class Option(BaseModel):
    key: str
    label: str


class AmbiguityCandidate(BaseModel):
    ambiguity_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    severity: RiskLevel = RiskLevel.P2
    candidate_options: list[Option] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source_refs: list[SourceRef] = Field(min_length=1)


class AmbiguityDetectionOutput(BaseModel):
    schema_version: str = "1.0"
    mission_id: int
    items: list[AmbiguityCandidate]


class AmbiguityResolveRequest(BaseModel):
    selected_option_key: str
    resolution_note: str | None = None
    status: Literal["RESOLVED", "DEFERRED", "OUT_OF_SCOPE"] = "RESOLVED"


class IntentCandidate(BaseModel):
    intent_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    business_goal: str = ""
    required_outcomes: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.P2
    source_refs: list[SourceRef] = Field(min_length=1)


class IntentDetectionOutput(BaseModel):
    schema_version: str = "1.0"
    mission_id: int
    items: list[IntentCandidate]


class IntentReviewRequest(BaseModel):
    action: Literal["approve", "reject"] = "approve"
    review_comment: str | None = None


class AmbiguityRead(BaseModel):
    id: int
    mission_id: int
    ambiguity_key: str
    title: str
    description: str
    severity: str
    status: str
    candidate_options_json: str
    selected_option_json: str
    ai_confidence: float
    resolution_note: str
    created_at: str | None = None
    updated_at: str | None = None


class IntentRead(BaseModel):
    id: int
    mission_id: int
    intent_key: str
    title: str
    business_goal: str
    risk_level: str
    review_status: str
    created_at: str | None = None
    updated_at: str | None = None
