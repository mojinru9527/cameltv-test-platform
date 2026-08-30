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
    # V3.2 data runtime step (V32-014 timeline)
    DATA = "DATA"


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
    # V3.2 data runtime evidence (V32-014)
    DATA_PLAN = "DATA_PLAN"
    FIXTURE_MANIFEST = "FIXTURE_MANIFEST"
    DB_BEFORE = "DB_BEFORE"
    DB_AFTER = "DB_AFTER"
    DB_CLEANUP_VERIFY = "DB_CLEANUP_VERIFY"


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


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.3 — Browser + Hybrid + Assisted Manual shared enums (V33).
# ────────────────────────────────────────────────────────────────────────────


class CommandPlanStatus(str, Enum):
    """CommandPlanVersion 状态。ACTIVE 不可变；其它版本可为 DRAFT/VALIDATED/STALE。"""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"


class BrowserSessionMode(str, Enum):
    """浏览器会话模式（V33-005 四种模式）。"""

    EXPLORE = "EXPLORE"
    REGRESSION = "REGRESSION"
    OBSERVE = "OBSERVE"
    MANUAL_ASSIST = "MANUAL_ASSIST"


class BrowserObservationEventType(str, Enum):
    NAVIGATION = "NAVIGATION"
    CLICK = "CLICK"
    INPUT = "INPUT"
    XHR = "XHR"
    DOM = "DOM"
    SCREENSHOT = "SCREENSHOT"
    CONSOLE = "CONSOLE"


class HealingProposalStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class HealingProposalType(str, Enum):
    LOCATOR = "LOCATOR"
    WAIT = "WAIT"
    NAVIGATION = "NAVIGATION"
    NON_BUSINESS_ACTION = "NON_BUSINESS_ACTION"


class ManualStepStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class UiAssetBindingStatus(str, Enum):
    """Legacy UI asset binding status (plan §2 ``ui_asset_bindings``)."""

    UNBOUND = "UNBOUND"
    BOUND = "BOUND"
    STALE = "STALE"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.4 — Durable Runtime + Network Worker + Security Plane shared enums
# (V34). Worker registry, capability routing, policy decision and approval
# vocabulary per the V3.4 plan §§3-6.
# ────────────────────────────────────────────────────────────────────────────


class WorkerStatus(str, Enum):
    """Worker 生命周期状态（V34-003 注册/心跳）。"""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DRAINING = "DRAINING"
    DISABLED = "DISABLED"


class NetworkZone(str, Enum):
    """Worker 网络分区。Production 业务仅 V3.6 才开放 PROD_RO。"""

    OFFICE = "OFFICE"
    TEST = "TEST"
    PROD_RO = "PROD_RO"


class Capability(str, Enum):
    """Worker Capability（V34-004 可路由能力）。"""

    HTTP = "HTTP"
    BROWSER = "BROWSER"
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    LOG = "LOG"
    KAFKA = "KAFKA"


class WorkflowType(str, Enum):
    """V3.4 编排工作流类型。"""

    SCENARIO_EXECUTION = "SCENARIO_EXECUTION"
    MISSION_DESIGN = "MISSION_DESIGN"


class WorkflowStatus(str, Enum):
    """Durable Run 的 Tester 可见状态（V3.4 §10 前端状态）。"""

    WAITING_WORKER = "WAITING_WORKER"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RETRYING = "RETRYING"
    RESUMING = "RESUMING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IdempotencyStatus(str, Enum):
    """Runtime 幂等键状态（V34-012）。"""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PolicyDecision(str, Enum):
    """Policy 网关判定（V34-010）。"""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ApprovalStatus(str, Enum):
    """审批请求状态（V34-011）。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class SecretRefStatus(str, Enum):
    """SecretRef metadata 状态（V34-008；永不返回 secret value）。"""

    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"


class PolicyType(str, Enum):
    """Policy Profile 类型。"""

    NETWORK_ZONE = "NETWORK_ZONE"
    CAPABILITY = "CAPABILITY"
    SECRET_SCOPE = "SECRET_SCOPE"
    DRIVER_ACTION = "DRIVER_ACTION"


class RuntimeResourceType(str, Enum):
    """幂等键资源类型（V34-012）。"""

    RUN = "RUN"
    DATA = "DATA"
    CLEANUP = "CLEANUP"
    ACTIVITY = "ACTIVITY"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.5 — Continuous Acceptance shared enums (V35). Fingerprint source,
# build observation, campaign/run-profile, trigger, and Quality Gate vocabulary
# per the V3.5 plan §§2-5.
# ────────────────────────────────────────────────────────────────────────────


class FingerprintSourceType(str, Enum):
    """指纹来源（V35-001）。"""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    WEBHOOK = "WEBHOOK"


class BuildObservationStatus(str, Enum):
    """BuildObservation 状态（V35-002）。"""

    NEW = "NEW"
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    EVALUATED = "EVALUATED"
    IGNORED = "IGNORED"


class CampaignType(str, Enum):
    """ExecutionCampaign 类型（V35-003）。"""

    IMPACTED = "IMPACTED"
    FULL = "FULL"
    SMOKE = "SMOKE"
    CUSTOM = "CUSTOM"


class RunProfileType(str, Enum):
    """RunProfile 类型（V35-004）。"""

    SMOKE = "SMOKE"
    FULL = "FULL"
    CUSTOM = "CUSTOM"


class ContinuousTriggerType(str, Enum):
    """Continuous Acceptance Trigger 类型（V35-008）. Uses a distinct name to avoid
    colliding with the V31 execution ``TriggerType`` (MANUAL/LEGACY_BRIDGE/SYSTEM)."""

    MANUAL = "MANUAL"
    SCHEDULE = "SCHEDULE"
    FINGERPRINT = "FINGERPRINT"
    WEBHOOK = "WEBHOOK"


class QualityGateResult(str, Enum):
    """Quality Gate 结果（V35-007）。"""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class CampaignScenarioRequired(str, Enum):
    """CampaignScenario 是否强制（V35-003）. P0 默认 mandatory."""

    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.6 — Production Evidence & Real-World Data Template shared enums
# (V36). Observation session / journey / masking / template / gap proposal
# vocabulary per the V3.6 plan §§2-12. Production 默认只读。
# ────────────────────────────────────────────────────────────────────────────


class ObservationMode(str, Enum):
    """生产观察会话模式（V36-002）。"""

    OBSERVE = "OBSERVE"
    READONLY_EXPLORE = "READONLY_EXPLORE"


class ObservationSessionStatus(str, Enum):
    """观察会话生命周期状态（V36-002，可恢复）。"""

    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JourneyEventType(str, Enum):
    """ObservedJourneyStep 事件类型（V36-002/004）。"""

    NAVIGATE = "NAVIGATE"
    XHR = "XHR"
    SEMANTIC = "SEMANTIC"
    SCROLL = "SCROLL"


class MaskingStrategy(str, Enum):
    """脱敏策略（V36-008）。"""

    REDACT = "REDACT"
    HASH = "HASH"
    TOKENIZE = "TOKENIZE"
    FAKE = "FAKE"
    PRESERVE = "PRESERVE"


class PiiClassification(str, Enum):
    """PII 分类（V36-007）。"""

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PERSON_NAME = "PERSON_NAME"
    ID_NUMBER = "ID_NUMBER"
    ADDRESS = "ADDRESS"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    TOKEN = "TOKEN"
    DEVICE_ID = "DEVICE_ID"
    IP = "IP"
    FREE_TEXT = "FREE_TEXT"


class TemplateValidationStatus(str, Enum):
    """Prod 模板校验状态（V36-010/011）。"""

    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"


class MaterializationStatus(str, Enum):
    """模板物化状态（V36-011）。"""

    PENDING = "PENDING"
    MATERIALIZING = "MATERIALIZING"
    READY = "READY"
    FAILED = "FAILED"


class ProdDbOperationType(str, Enum):
    """生产 DB 探索操作类型（V36-005/006）。"""

    SELECT = "SELECT"
    EXPLAIN = "EXPLAIN"


class GapProposalKind(str, Enum):
    """Evidence Gap Proposal 类型（V36-012）。"""

    SOURCE_ARTIFACT = "SOURCE_ARTIFACT"
    AMBIGUITY = "AMBIGUITY"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    SCENARIO_GAP = "SCENARIO_GAP"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.7 — Impact Analysis + Smart Regression shared enums (V37).
# ChangeSet / Lineage / Impact / Regression Selection vocabulary per the V3.7
# plan §§2-10. String-valued, stable across SQLite/PostgreSQL.
# ────────────────────────────────────────────────────────────────────────────


class ChangeSetType(str, Enum):
    """ChangeSet 来源类型（V37-002 各种 Diff Provider）。"""

    PRD = "PRD"
    OPENAPI = "OPENAPI"
    DB_SCHEMA = "DB_SCHEMA"
    UI_DISCOVERY = "UI_DISCOVERY"
    ENVIRONMENT = "ENVIRONMENT"
    HISTORICAL_RISK = "HISTORICAL_RISK"


class ChangeSetStatus(str, Enum):
    """ChangeSet 生命周期状态（V37-003..007）。"""

    DETECTED = "DETECTED"
    ANALYZED = "ANALYZED"
    SUPERSEDED = "SUPERSEDED"


class ChangeItemKind(str, Enum):
    """单个差异项的变更类型（V37-003..007）。"""

    ADDED = "ADDED"
    CHANGED = "CHANGED"
    DELETED = "DELETED"


class LineageNodeType(str, Enum):
    """Lineage 节点类型（V37-001；plan §3）。"""

    SOURCE_ARTIFACT = "SOURCE_ARTIFACT"
    SOURCE_FRAGMENT = "SOURCE_FRAGMENT"
    SCOPE_ITEM = "SCOPE_ITEM"
    TEST_INTENT = "TEST_INTENT"
    CONTRACT_RULE = "CONTRACT_RULE"
    SCENARIO = "SCENARIO"
    SCENARIO_VERSION = "SCENARIO_VERSION"
    ORACLE = "ORACLE"
    API_ENDPOINT = "API_ENDPOINT"
    PAGE = "PAGE"
    DATA_ENTITY = "DATA_ENTITY"
    OBSERVED_JOURNEY = "OBSERVED_JOURNEY"
    EXECUTION_RUN = "EXECUTION_RUN"
    DEFECT = "DEFECT"


class LineageEdgeType(str, Enum):
    """Lineage 边类型（V37-001；plan §3）。"""

    DERIVES_FROM = "DERIVES_FROM"
    APPLIES_TO = "APPLIES_TO"
    IMPLEMENTS = "IMPLEMENTS"
    VERIFIES = "VERIFIES"
    BINDS = "BINDS"
    MAPPED_TO = "MAPPED_TO"
    OBSERVED_AS = "OBSERVED_AS"
    FAILED_IN = "FAILED_IN"
    DEFECT_OF = "DEFECT_OF"
    CONTRACTED_FOR = "CONTRACTED_FOR"


class RiskHint(str, Enum):
    """风险提示来源（V37-007 HistoricalRisk + 权重）。"""

    P0_RULE = "P0_RULE"
    CONTRACT_RULE = "CONTRACT_RULE"
    LAST_BUSINESS_FAIL = "LAST_BUSINESS_FAIL"
    HISTORICAL_DEFECT = "HISTORICAL_DEFECT"
    RECENT_CHANGE = "RECENT_CHANGE"
    PROD_REAL_WORLD = "PROD_REAL_WORLD"
    UNKNOWN_CHANGE = "UNKNOWN_CHANGE"
    NONE = "NONE"


class ImpactRunStatus(str, Enum):
    """ImpactAnalysisRun 生命周期状态（V37-008）。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImpactDecision(str, Enum):
    """ImpactResult 决策（V37-008）。"""

    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    FALLBACK = "FALLBACK"


class SelectionType(str, Enum):
    """RegressionSelection 类型（V37-009/010）。"""

    SMART = "SMART"
    FULL = "FULL"
    SMOKE = "SMOKE"
    CUSTOM = "CUSTOM"


class SelectionDecision(str, Enum):
    """RegressionSelection 中单个 Scenario 的入组决策（V37-009）。"""

    SELECTED = "SELECTED"
    EXCLUDED = "EXCLUDED"
    FALLBACK = "FALLBACK"


# ────────────────────────────────────────────────────────────────────────────
# AITDE V3.8 — AI QA Closed Loop shared enums (V38).
# Failure triage, healing policy, flaky, strategy performance, scenario gap,
# suggestion, human feedback and model-evaluation vocabulary per the V3.8 plan
# §§1-12. String-valued, stable across SQLite/PostgreSQL.
# ────────────────────────────────────────────────────────────────────────────


class FailureHypothesisStatus(str, Enum):
    """FailureHypothesis 生命周期状态（V38-002/003）。"""

    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class FailureClassification(str, Enum):
    """失败归因分类（V38-002；AI 只产出 hypothesis，不修改 Outcome）。"""

    BUSINESS_LOGIC_SUSPECTED = "BUSINESS_LOGIC_SUSPECTED"
    AUTOMATION_ISSUE_SUSPECTED = "AUTOMATION_ISSUE_SUSPECTED"
    DATA_ISSUE_SUSPECTED = "DATA_ISSUE_SUSPECTED"
    ENV_ISSUE_SUSPECTED = "ENV_ISSUE_SUSPECTED"
    FLAKY_SUSPECTED = "FLAKY_SUSPECTED"
    UNKNOWN = "UNKNOWN"


class HealingPolicyDecision(str, Enum):
    """Healing Policy 判定（V38-004；仅 Action diff 允许）。"""

    ALLOW = "ALLOW"
    REJECT = "REJECT"


class FlakySignalType(str, Enum):
    """Flaky 信号类型（V38-006；仅 AUTOMATION/ENV 波动纳入）。"""

    RERUN_PASS = "RERUN_PASS"
    INTERMITTENT_ERROR = "INTERMITTENT_ERROR"
    TIMEOUT = "TIMEOUT"
    STALE_LOCATOR = "STALE_LOCATOR"
    ENV_FLAP = "ENV_FLAP"


class FlakyClassification(str, Enum):
    """Flaky 聚类分类（V38-007）。"""

    FLAKY = "FLAKY"
    STABLE = "STABLE"
    FLAPPY = "FLAPPY"
    UNCLASSIFIED = "UNCLASSIFIED"


class SuggestionType(str, Enum):
    """AI Suggestion 类型（V38-011 Inbox）。"""

    HEALING = "HEALING"
    DATA_STRATEGY = "DATA_STRATEGY"
    SCENARIO_GAP = "SCENARIO_GAP"
    RISK = "RISK"
    TRIAGE = "TRIAGE"


class SuggestionStatus(str, Enum):
    """AI Suggestion 生命周期状态（V38-011）。"""

    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    EXPIRED = "EXPIRED"


class FeedbackType(str, Enum):
    """Human Feedback 类型（V38-012；append-only）。"""

    CORRECTION = "CORRECTION"
    CONFIRMATION = "CONFIRMATION"
    REJECTION = "REJECTION"


class StrategyType(str, Enum):
    """数据/browser 策略类型（V38-008）。"""

    DATA = "DATA"
    API = "API"
    DB_FIXTURE = "DB_FIXTURE"
    WORKFLOW = "WORKFLOW"
    BROWSER = "BROWSER"


class ScenarioGapType(str, Enum):
    """Scenario Gap 来源类型（V38-010）。"""

    PROD_NEW_STATE = "PROD_NEW_STATE"
    HISTORICAL_DEFECT = "HISTORICAL_DEFECT"
    REPEATED_BUSINESS_FAIL = "REPEATED_BUSINESS_FAIL"
    UNCOVERED_CONTRACT_RULE = "UNCOVERED_CONTRACT_RULE"
    UNCOVERED_JOURNEY = "UNCOVERED_JOURNEY"
    NEW_OPENAPI_STATE = "NEW_OPENAPI_STATE"


class GapCandidateStatus(str, Enum):
    """ScenarioGapCandidate 生命周期状态（V38-010；proposal only）。"""

    OPEN = "OPEN"
    CONVERTED = "CONVERTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ModelEvaluationStatus(str, Enum):
    """ModelEvaluationRun 生命周期状态（V38-013）。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AutoRetryDecision(str, Enum):
    """AutoRetry Policy 判定（V38-014）。"""

    RETRY = "RETRY"
    NO_RETRY = "NO_RETRY"
    INVALID = "INVALID"
