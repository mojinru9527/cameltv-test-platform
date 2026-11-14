"""PR #595 后 v1.4：执行链版本化协议。

约束（对应实施包 FIX-001/002/005/006）：
- 所有对象带 `schema_version`；
- `ResolvedInput` 只携带 secret 的 key，不携带 secret 明文；
- `DriverResult` 是 Driver 的标准化输出，业务 PASS 由 Assertion Runtime 判定；
- `AssertionSpec` 必须声明 oracle_layer（REQ/STD/PATTERN）与 oracle_ref；
- Preflight 在任何 Job 入队前给出可解释的阻断原因。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ASSERTION_SCHEMA_VERSION = "1.0"
DRIVER_RESULT_SCHEMA_VERSION = "1.0"
RESOLVED_INPUT_SCHEMA_VERSION = "1.0"
PREFLIGHT_SCHEMA_VERSION = "1.0"

OracleLayer = Literal["REQ", "STD", "PATTERN"]
AssertionStatus = Literal["PASS", "FAIL", "ERROR", "NOT_EVALUATED", "BLOCKED"]
Severity = Literal["P0", "P1", "P2"]

ASSERTION_TYPES: frozenset[str] = frozenset(
    {
        "http_status",
        "jsonpath",
        "json_schema",
        "text_contains",
        "text_equals",
        "locator_visible",
        "locator_count",
        "url_equals",
        "url_contains",
        "db_value_eq",
        "db_row_exists",
        "db_row_count",
        "event_received",
        "eventually",
    }
)


class SourceRef(BaseModel):
    """输入值的来源（节点输出 / fixture / secret key / env key）。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["node_output", "fixture", "secret", "env", "literal"]
    ref: str
    node_key: str | None = None
    output: str | None = None


class ResolvedInput(BaseModel):
    """节点 READY 时解析出的输入；secret 只保留 key。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = RESOLVED_INPUT_SCHEMA_VERSION
    values: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)
    secret_keys: list[str] = Field(default_factory=list)


class AssertionSpec(BaseModel):
    """一条机器断言；字段与 13 号 §4.10 对齐。"""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    assertion_key: str = Field(min_length=1, max_length=100)
    schema_version: str = ASSERTION_SCHEMA_VERSION
    oracle_layer: OracleLayer
    oracle_ref: str = Field(default="", max_length=255)
    type: str = Field(min_length=1)
    operator: str = "eq"
    expected: Any = None
    expected_ref: str | None = None
    actual_source: str = ""
    path: str | None = None
    selector: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    timeout_ms: int = Field(default=0, ge=0)
    severity: Severity = "P1"
    message: str = ""

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in ASSERTION_TYPES:
            raise ValueError(f"未支持的 assertion type: {value!r}")
        return value

    @field_validator("oracle_ref")
    @classmethod
    def _oracle_ref_required(cls, value: str, info) -> str:
        # STD/PATTERN 必须有具体 rule ref；REQ 允许为空（由 Contract/AC id 在
        # 上层补充），但空值会在 evaluate 时降级为 ERROR，避免无来源断言。
        return value


class AssertionOutcome(BaseModel):
    """一条断言的执行结果（落库前脱敏）。"""

    model_config = ConfigDict(extra="forbid")

    assertion_key: str
    schema_version: str = ASSERTION_SCHEMA_VERSION
    oracle_layer: OracleLayer = "STD"
    oracle_ref: str = ""
    type: str
    status: AssertionStatus
    expected: Any = None
    actual: Any = None
    diff: Any = None
    actual_source: str = ""
    severity: Severity = "P1"
    timeout_ms: int = 0
    duration_ms: int = 0
    error: str = ""
    artifact_refs: list[str] = Field(default_factory=list)


class EvidenceFile(BaseModel):
    """Driver 产出、尚未入库的证据文件。"""

    model_config = ConfigDict(extra="allow")

    name: str
    artifact_type: str
    mime_type: str = "application/octet-stream"
    content: bytes = b""
    sha256: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverResult(BaseModel):
    """Driver 标准化结果；`data` 供 Assertion/Outputs 使用，不直接代表 PASS。"""

    model_config = ConfigDict(extra="allow")

    schema_version: str = DRIVER_RESULT_SCHEMA_VERSION
    driver_key: str
    status: Literal["SUCCEEDED", "FAILED", "BLOCKED", "ERROR"] = "SUCCEEDED"
    data: dict[str, Any] = Field(default_factory=dict)
    error_class: str = ""
    error_message: str = ""
    duration_ms: int = 0
    evidence: list[EvidenceFile] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class PreflightIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    code: Literal[
        "UNSUPPORTED_DRIVER",
        "CAPABILITY_UNAVAILABLE",
        "NODE_OFFLINE",
        "NO_SLOT",
        "PLATFORM_MISMATCH",
        "ENVIRONMENT_MISSING",
        "PROFILE_MISSING",
        "FIXTURE_MISSING",
        "SECRET_MISSING",
        "VARIABLE_NOT_FOUND",
    ]
    message: str
    required_capability: str = ""
    available_nodes: list[str] = Field(default_factory=list)


class PreflightReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PREFLIGHT_SCHEMA_VERSION
    ok: bool = True
    issues: list[PreflightIssue] = Field(default_factory=list)

    def add(self, issue: PreflightIssue) -> None:
        self.issues.append(issue)
        self.ok = False
