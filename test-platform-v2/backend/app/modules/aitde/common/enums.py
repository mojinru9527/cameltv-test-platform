"""AITDE V3 shared enums (V30-001/V30-010).

Central enum definitions for the Mission aggregate's type/status/acceptance
vocabulary. String-valued so they map cleanly to ``String`` columns and remain
stable across DB backends.
"""
from __future__ import annotations

from enum import Enum


class MissionType(str, Enum):
    """Mission 类型（V3.0 先支持 VERSION，其余枚举保留）。"""

    VERSION = "VERSION"
    FEATURE = "FEATURE"
    HOTFIX = "HOTFIX"
    REGRESSION = "REGRESSION"
    EXPLORATORY = "EXPLORATORY"


class MissionStatus(str, Enum):
    """Mission 生命周期状态（V3.0 主链 DRAFT → ... → SCENARIO_READY → ARCHIVED）。"""

    DRAFT = "DRAFT"
    SOURCE_READY = "SOURCE_READY"
    SCOPE_ANALYZING = "SCOPE_ANALYZING"
    SCOPE_REVIEW = "SCOPE_REVIEW"
    CONTRACT_BUILDING = "CONTRACT_BUILDING"
    CONTRACT_REVIEW = "CONTRACT_REVIEW"
    CONTRACT_FROZEN = "CONTRACT_FROZEN"
    SCENARIO_BUILDING = "SCENARIO_BUILDING"
    SCENARIO_REVIEW = "SCENARIO_REVIEW"
    SCENARIO_READY = "SCENARIO_READY"
    ARCHIVED = "ARCHIVED"


class AcceptanceStatus(str, Enum):
    """验收状态（Gate 结果；绝对禁止 0 条执行 → PASS）。"""

    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_READY = "NOT_READY"
    PASS = "PASS"
    FAIL = "FAIL"


class SourceType(str, Enum):
    """SourceArtifact 类型（V3.0 真正支持 REQUIREMENT/OPENAPI/MANUAL_NOTE）。"""

    REQUIREMENT = "REQUIREMENT"
    OPENAPI = "OPENAPI"
    WIKI = "WIKI"
    PROTOTYPE = "PROTOTYPE"
    HISTORICAL_CASE = "HISTORICAL_CASE"
    HISTORICAL_DEFECT = "HISTORICAL_DEFECT"
    MANUAL_NOTE = "MANUAL_NOTE"


class SourceRole(str, Enum):
    """Mission-Source 关联角色。"""

    REQUIREMENT = "REQUIREMENT"
    CONTRACT = "CONTRACT"
    SUPPORTING = "SUPPORTING"
    HISTORY = "HISTORY"


class ParseStatus(str, Enum):
    """Source 解析状态。"""

    PENDING = "PENDING"
    PARSING = "PARSING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class ScopeType(str, Enum):
    FEATURE = "FEATURE"
    BUSINESS_FLOW = "BUSINESS_FLOW"
    PAGE = "PAGE"
    API = "API"
    DATA_STATE = "DATA_STATE"
    RISK = "RISK"
    REGRESSION_AREA = "REGRESSION_AREA"


class ScopeDecision(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class TestDepth(str, Enum):
    FULL = "FULL"
    REGRESSION = "REGRESSION"
    SMOKE = "SMOKE"
    OBSERVE = "OBSERVE"


class RiskLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ReviewStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActorType(str, Enum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"


class AmbiguityStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ContractVersionStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWING = "REVIEWING"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"


class ProposalTargetType(str, Enum):
    CONTRACT = "CONTRACT"
    SCENARIO = "SCENARIO"
    ORACLE = "ORACLE"


class ProposalStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class OracleType(str, Enum):
    UI = "UI"
    API = "API"
    DB = "DB"
    EVENT = "EVENT"
    LOG = "LOG"
    CONTRACT = "CONTRACT"
    VISUAL = "VISUAL"
    PERFORMANCE = "PERFORMANCE"


class ScenarioReviewStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_CHANGE = "REQUEST_CHANGE"


class AIOperationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.1 — Unified Execution + Proof Replay shared enums
# (V31). These are the frozen V3.x public outcome taxonomy per the V3.1 plan.
# ────────────────────────────────────────────────────────────────────────────


class AdapterType(str, Enum):
    """ScenarioAdapter 绑定类型。"""

    MANUAL = "MANUAL"
    API = "API"
    UI = "UI"
    DB = "DB"
    HYBRID = "HYBRID"


class AdapterStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    STALE = "STALE"
    DISABLED = "DISABLED"


class RunStatus(str, Enum):
    """runtime_status：执行器调度状态，与 outcome 分离。"""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class Outcome(str, Enum):
    """正式结论（V3.x 公共枚举，冻结）。AI 不拥有 PASS/FAIL 裁决权。"""

    PASS = "PASS"
    BUSINESS_FAIL = "BUSINESS_FAIL"
    AUTOMATION_FAIL = "AUTOMATION_FAIL"
    DATA_FAIL = "DATA_FAIL"
    ENV_FAIL = "ENV_FAIL"
    ASSERTION_ERROR = "ASSERTION_ERROR"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class TriggerType(str, Enum):
    MANUAL = "MANUAL"
    LEGACY_BRIDGE = "LEGACY_BRIDGE"
    SYSTEM = "SYSTEM"


class StepType(str, Enum):
    ACTION = "ACTION"
    API = "API"
    UI = "UI"
    DB = "DB"
    ASSERT = "ASSERT"
    SYSTEM = "SYSTEM"
    LEGACY = "LEGACY"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AssertionResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    ERROR = "ERROR"


class EvidenceType(str, Enum):
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


class SanitizationStatus(str, Enum):
    PENDING = "PENDING"
    SANITIZED = "SANITIZED"
    REJECTED = "REJECTED"


class LegacyExecutionType(str, Enum):
    API_TASK_ITEM = "API_TASK_ITEM"
    UI_RUN = "UI_RUN"
    TEST_EXECUTION = "TEST_EXECUTION"


class SnapshotSource(str, Enum):
    """环境快照来源：自动捕获或人工 build_label 登记。"""

    AUTO = "AUTO"
    MANUAL = "MANUAL"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.2 — Data + DB Runtime shared enums (V32). DataSources, plans,
# fixtures and the data runtime vocabulary. PROD_TEMPLATE is reserved only;
# the V3.2 production data-source template capability is deferred to V3.6.
# ────────────────────────────────────────────────────────────────────────────


class DataSourceType(str, Enum):
    """Data Source 类型（V32-001）。PROD_TEMPLATE 仅预留枚举，不在此版本启用。"""

    STATIC = "STATIC"
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    API = "API"
    WORKFLOW = "WORKFLOW"
    PROD_TEMPLATE = "PROD_TEMPLATE"


class DataSourceAccessMode(str, Enum):
    """Data Source 访问模式。V3.2 仅允许 Test 环境 READWRITE；Production 默认只读。"""

    READONLY = "READONLY"
    READWRITE = "READWRITE"


class DataSourceStatus(str, Enum):
    """Data Source 连接/可用状态。"""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class DataRequirementSharingPolicy(str, Enum):
    """数据需求共享策略：独占或只读共享。"""

    EXCLUSIVE = "EXCLUSIVE"
    SHARED_READONLY = "SHARED_READONLY"


class DataRequirementCleanupPolicy(str, Enum):
    """数据需求清理策略。"""

    ALWAYS = "ALWAYS"
    ON_SUCCESS = "ON_SUCCESS"
    MANUAL = "MANUAL"


class DataPlanStatus(str, Enum):
    """数据计划生命周期状态。"""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    DONE = "DONE"
    FAILED = "FAILED"


class DataPlanStrategy(str, Enum):
    """数据计划策略（顺序：Existing → API → DB Fixture → Workflow）。"""

    EXISTING = "EXISTING"
    API_BUILDER = "API_BUILDER"
    DB_FIXTURE = "DB_FIXTURE"
    WORKFLOW = "WORKFLOW"


class DataPlanStepType(str, Enum):
    """数据计划步骤类型。"""

    FIND = "FIND"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    VERIFY = "VERIFY"
    LEASE = "LEASE"
    SNAPSHOT = "SNAPSHOT"
    CLEANUP = "CLEANUP"


class FixtureStatus(str, Enum):
    """Fixture 生命周期状态机。"""

    PROVISIONING = "PROVISIONING"
    READY = "READY"
    LEASED = "LEASED"
    IN_USE = "IN_USE"
    CLEANING = "CLEANING"
    CLEANED = "CLEANED"
    FAILED = "FAILED"


class FixtureLeaseStatus(str, Enum):
    """Fixture 租约状态。"""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class SnapshotType(str, Enum):
    """数据快照类型。"""

    BEFORE = "BEFORE"
    AFTER = "AFTER"
    CLEANUP_VERIFY = "CLEANUP_VERIFY"


class CleanupStatus(str, Enum):
    """清理记录状态。"""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
