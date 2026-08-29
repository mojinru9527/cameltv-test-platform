"""Contract Pydantic schemas (V30-055/V30-056)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import RiskLevel
from app.modules.aitde.scope.schemas import SourceRef


class ContractRule(BaseModel):
    rule_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    kind: str = "BUSINESS_RULE"
    statement: str = ""
    risk_level: RiskLevel = RiskLevel.P2
    source_type: str = "REQUIREMENT_EXPLICIT"
    source_refs: list[SourceRef] = Field(min_length=1)


class ContractOutcome(BaseModel):
    outcome_key: str = Field(min_length=1, max_length=128)
    statement: str = ""
    source_type: str = "TESTER_APPROVED"
    source_refs: list[SourceRef] = Field(min_length=1)


class ContractSnapshot(BaseModel):
    schema_version: str = "1.0"
    mission_id: int
    scope_revision: str = ""
    rules: list[ContractRule] = Field(default_factory=list)
    required_outcomes: list[ContractOutcome] = Field(default_factory=list)


class ContractGenerateRequest(BaseModel):
    model: str | None = None
    force: bool = False


class ContractFreezeRequest(BaseModel):
    expected_version: int
    confirm: bool = False


class ContractVersionRead(BaseModel):
    id: int
    contract_id: int
    version_no: int
    status: str
    content_hash: str
    snapshot_json: str
    created_at: str | None = None
    approved_at: str | None = None


class ContractDiffRule(BaseModel):
    rule_key: str
    change: str  # added | removed | changed
    title: str | None = None


class ContractDiffRead(BaseModel):
    base_version: int
    target_version: int
    added: list[ContractDiffRule]
    removed: list[ContractDiffRule]
    changed: list[ContractDiffRule]
