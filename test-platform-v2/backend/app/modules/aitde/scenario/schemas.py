"""Scenario / Oracle Pydantic schemas (V30-061..V30-067)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import OracleType, RiskLevel
from app.modules.aitde.scope.schemas import SourceRef


class OracleCandidate(BaseModel):
    oracle_key: str = Field(min_length=1, max_length=128)
    oracle_type: OracleType
    target: dict[str, Any] = Field(default_factory=dict)
    operator: str = "eq"
    expected_value: dict[str, Any] = Field(default_factory=dict)
    source_type: str = "AI_INFERRED"
    source_refs: list[SourceRef] = Field(min_length=1)
    required: bool = True
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)


class ScenarioCandidate(BaseModel):
    scenario_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    business_goal: str = ""
    priority: RiskLevel = RiskLevel.P2
    risk_level: RiskLevel = RiskLevel.P2
    given: dict[str, Any] = Field(default_factory=dict)
    when: dict[str, Any] = Field(default_factory=dict)
    expected_state: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(min_length=1)
    oracles: list[OracleCandidate] = Field(default_factory=list)


class ScenarioDesignOutput(BaseModel):
    schema_version: str = "1.0"
    contract_version_id: int
    mission_id: int
    items: list[ScenarioCandidate]


class ScenarioReviewRequest(BaseModel):
    action: Literal["approve", "reject", "request_change"] = "approve"
    comment: str | None = None


class OracleReviewRequest(BaseModel):
    action: Literal["approve", "reject"] = "approve"
    required: bool | None = None
    comment: str | None = None


class FeatureStep(BaseModel):
    step: int
    description: str


class FunctionalProjectionRead(BaseModel):
    scenario_key: str
    title: str
    priority: str
    preconditions: list[str]
    steps: list[FeatureStep]
    expected_results: list[str]
