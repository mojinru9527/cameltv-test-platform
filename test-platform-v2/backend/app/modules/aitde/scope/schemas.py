"""Scope Pydantic schemas (V30-031/V30-036).

The AI output contract is strict: source refs are mandatory, confidence is a
0..1 float and enums are closed. Anything invalid is rejected before persist.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.aitde.common.enums import (
    RiskLevel,
    ScopeDecision,
    ScopeType,
    TestDepth,
)


class SourceRef(BaseModel):
    artifact_id: int
    fragment_id: int | None = None
    location: str | None = None


class ScopeAnalysisCandidate(BaseModel):
    scope_key: str = Field(min_length=1, max_length=128)
    scope_type: ScopeType
    name: str = Field(min_length=1, max_length=255)
    decision: ScopeDecision
    test_depth: TestDepth
    risk_level: RiskLevel
    reason: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    source_refs: list[SourceRef] = Field(min_length=1)

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v


class ScopeAnalysisOutput(BaseModel):
    schema_version: str = "1.0"
    mission_id: int
    items: list[ScopeAnalysisCandidate]


class ScopeAnalysisRequest(BaseModel):
    model: str | None = None
    force: bool = False


class ScopeReviewItem(BaseModel):
    scope_key: str
    decision: ScopeDecision
    action: Literal["approve", "reject"] = "approve"
    reason: str | None = None


class ScopeBulkReviewRequest(BaseModel):
    items: list[ScopeReviewItem] = Field(min_length=1)


class ScopeSummary(BaseModel):
    total: int
    approved: int
    rejected: int
    proposed: int
    review_progress: float
    include_count: int
    exclude_count: int


class ScopeItemRead(BaseModel):
    id: int
    mission_id: int
    scope_key: str
    scope_type: str
    name: str
    decision: str
    test_depth: str
    risk_level: str
    reason: str
    ai_confidence: float
    review_status: str
    created_by_type: str
    created_at: str | None = None
    updated_at: str | None = None
