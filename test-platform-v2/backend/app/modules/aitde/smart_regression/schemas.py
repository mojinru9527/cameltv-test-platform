"""AITDE V3.7 Impact Analysis + Smart Regression API schemas (V37)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DetectIn(BaseModel):
    """Detect a ChangeSet of a given type from a baseline/current snapshot."""

    change_type: str = Field(
        ...,
        description=(
            "PRD | OPENAPI | DB_SCHEMA | UI_DISCOVERY | ENVIRONMENT | HISTORICAL_RISK"
        ),
    )
    baseline: dict = Field(default_factory=dict)
    current: dict = Field(default_factory=dict)
    source_from_ref: str | None = None
    source_to_ref: str | None = None


class RiskSignalIn(BaseModel):
    scenario_id: int
    scenario_version_id: int | None = None
    risk_hint: str = "NONE"
    reason: str = ""
    source_refs: list[dict] = Field(default_factory=list)


class HistoricalRiskDetectIn(BaseModel):
    """Detect a HISTORICAL_RISK ChangeSet from explicit risk signals."""

    signals: list[RiskSignalIn] = Field(default_factory=list)


class SelectionIn(BaseModel):
    """Generate a regression selection from an impact run."""

    selection_type: str = "SMART"
    build_observation_id: int | None = None


class CampaignIn(BaseModel):
    """Freeze a regression selection into a V3.5 ExecutionCampaign."""

    name: str = Field(default="Smart Regression", max_length=128)
    environment_id: int = 0


class EdgeAddIn(BaseModel):
    """Manually add a lineage edge (Tester curation, V37-001)."""

    from_type: str
    from_id: int
    to_type: str
    to_id: int
    edge_type: str
    source_refs: list[dict] = Field(default_factory=list)
    confidence: float = 1.0
