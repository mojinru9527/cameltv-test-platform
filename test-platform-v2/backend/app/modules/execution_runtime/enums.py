"""Execution-runtime enums (platform simplification: needed subset only).

Only the enums referenced by the retained execution chain
(ExecutionRun / Scenario / Oracle / evidence completeness) are kept here;
the rest were deleted together with the AITDE domain.
"""

from __future__ import annotations

from enum import StrEnum



class AdapterStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    STALE = "STALE"
    DISABLED = "DISABLED"


class AdapterType(StrEnum):
    """ScenarioAdapter 绑定类型。"""

    MANUAL = "MANUAL"
    API = "API"
    UI = "UI"
    DB = "DB"
    HYBRID = "HYBRID"


class AssertionResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    ERROR = "ERROR"


class AssertionTrustStatus(StrEnum):
    """一条 Assertion 在 Release Gate 中能获得的信任级别。

    TRUSTED            -> 绑定真实 TestOracle，可进入 Trusted Release Gate
    LEGACY_UNVERIFIED  -> 来自 v1.x CommandPlan assert / 历史数据，不得阻塞或判决 Trusted PASS
    INVALID            -> 引用不存在的 oracle / 已冻结但被篡改
    """

    TRUSTED = "TRUSTED"
    LEGACY_UNVERIFIED = "LEGACY_UNVERIFIED"
    INVALID = "INVALID"


class EvidenceIntegrityStatus(StrEnum):
    """EvidenceArtifact 物理完整性状态（TRUST-004）。

    只有 storage_uri 非空 + content_hash 为合法 sha256 + size_bytes > 0 +
    sanitization_status == SANITIZED + integrity_status == VERIFIED 的 artifact
    才可用于 Required Evidence。任何一步失败不得标记 COMPLETE。
    """

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    CORRUPT = "CORRUPT"


class EvidenceStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class EvidenceType(StrEnum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    SCREENSHOT = "SCREENSHOT"
    VIDEO = "VIDEO"
    PW_TRACE = "PW_TRACE"
    HAR = "HAR"
    DOM = "DOM"
    CONSOLE = "CONSOLE"
    LOG = "LOG"
    ASSERTION = "ASSERTION"
    ENV_SNAPSHOT = "ENV_SNAPSHOT"
    LEGACY_ARTIFACT = "LEGACY_ARTIFACT"
    # V3.2 data runtime evidence (V32-014)
    DATA_PLAN = "DATA_PLAN"
    FIXTURE_MANIFEST = "FIXTURE_MANIFEST"
    DB_BEFORE = "DB_BEFORE"
    DB_AFTER = "DB_AFTER"
    DB_CLEANUP_VERIFY = "DB_CLEANUP_VERIFY"


class LegacyExecutionType(StrEnum):
    API_TASK_ITEM = "API_TASK_ITEM"
    UI_RUN = "UI_RUN"
    TEST_EXECUTION = "TEST_EXECUTION"


class OracleBindingType(StrEnum):
    """OracleBinding 绑定类型：回答 “Actual 去哪里拿”。

    Expected 永远来自 ``TestOracle.expected_value_json``；Binding 只描述 observation
    的取数路径（HTTP status / JSONPath / UI / DB column / event / log）。
    """

    API_STATUS = "API_STATUS"
    API_JSONPATH = "API_JSONPATH"
    UI_TEXT = "UI_TEXT"
    UI_VISIBLE = "UI_VISIBLE"
    UI_ATTRIBUTE = "UI_ATTRIBUTE"
    DB_COLUMN = "DB_COLUMN"
    EVENT_FIELD = "EVENT_FIELD"
    LOG_PATTERN = "LOG_PATTERN"


class OracleSourceType(StrEnum):
    """AssertionResult / Oracle 的来源类型。

    TEST_ORACLE                -> 真实 TestOracle（唯一“标准答案”，TRUSTED）
    LEGACY_COMMAND_ASSERT      -> 旧 CommandPlan steps[].asserts（可执行但不可信）
    LEGACY_EXECUTION           -> 历史 execution 自报（不可信）
    """

    TEST_ORACLE = "TEST_ORACLE"
    LEGACY_COMMAND_ASSERT = "LEGACY_COMMAND_ASSERT"
    LEGACY_EXECUTION = "LEGACY_EXECUTION"


class OracleType(StrEnum):
    UI = "UI"
    API = "API"
    DB = "DB"
    EVENT = "EVENT"
    LOG = "LOG"
    CONTRACT = "CONTRACT"
    VISUAL = "VISUAL"
    PERFORMANCE = "PERFORMANCE"


class ReviewStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskLevel(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RunStatus(StrEnum):
    """runtime_status：执行器调度状态，与 outcome 分离。"""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class SanitizationStatus(StrEnum):
    PENDING = "PENDING"
    SANITIZED = "SANITIZED"
    REJECTED = "REJECTED"


class ScenarioReviewStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_CHANGE = "REQUEST_CHANGE"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StepType(StrEnum):
    ACTION = "ACTION"
    API = "API"
    UI = "UI"
    DB = "DB"
    ASSERT = "ASSERT"
    SYSTEM = "SYSTEM"
    LEGACY = "LEGACY"
    # V3.2 data runtime step (V32-014 timeline)
    DATA = "DATA"


class TriggerType(StrEnum):
    MANUAL = "MANUAL"
    LEGACY_BRIDGE = "LEGACY_BRIDGE"
    SYSTEM = "SYSTEM"
