"""统一导出所有模型，确保 Base.metadata 能感知全部表。

平台简化批次：AITDE/DSH/报告/数据集/通知/集成/组织/AI 本地管线/知识图谱 UI 域
的模型已随模块删除；保留模型清单如下。
"""

from app.models.ai_gateway_cache import AiResponseCache
from app.models.ai_shadow_run import AiShadowRun
from app.models.ai_provider import AiProvider
from app.models.ai_task import AiTask
from app.models.ai_job import AiAgent
from app.models.ai_agent_token import AiAgentToken
from app.models.execution_job import ExecutionJob
from app.models.impact_edge import ImpactEdge
from app.models.reuse_suggestion import ReuseSuggestionEvent
from app.models.plan_execution_job import PlanExecutionJob
from app.models.interaction_edge import InteractionEdge
from app.models.api_asset import ApiEndpoint, ApiExecutionTask, ApiExecutionTaskItem, ApiImportBatch, ApiService
from app.models.api_token import ApiToken
from app.modules.campaign_execution.models import CampaignItem, TestCampaign
from app.models.audit import AuditLog
from app.models.defect import Defect
from app.models.environment import Environment, EnvironmentVariable
from app.models.invite_code import InviteCode
from app.models.lanhu_evidence import (
    LanhuEvidenceAsset,
    LanhuEvidenceJob,
    LanhuEvidencePage,
    LanhuOcrBlock,
)
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeEntity,
    KnowledgeRelation,
    KnowledgeSource,
    KnowledgeVector,
)
from app.models.model_usage import ModelUsageLedger
from app.models.project import Project, ProjectMember
from app.models.project_invite import ProjectInvite
from app.models.quality_gate import QualityGateConfig
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.requirement_review import RequirementReview
from app.models.runner_execution import RunnerExecutionTask
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.test_case import TestCase
from app.models.test_case_category import TestCaseDomain, TestCaseModule
from app.models.test_case_review import TestCaseReviewTransition
from app.models.test_case_version import TestCaseVersion
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_schedule import TestSchedule, TestScheduleRun
from app.models.ui_test import UiTestJob, UiTestRun, UiTestScript
from app.models.user import User
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.models.version_task_plan import VersionTaskPlanItem
from app.models.version_task_run import VersionTaskRun
from app.models.version_knowledge import VersionKnowledgeRecord
from app.models.wiki import (
    WikiIngestJob,
    WikiLink,
    WikiPage,
    WikiRawSource,
)

# 执行运行时（从 AITDE 抽离的最小执行模型，表名与迁移历史保持一致）
from app.modules.execution_runtime.models import (  # noqa: E402
    AssertionResult,
    EnvironmentSnapshot,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
    LegacyExecutionLink,
    ReplayManifest,
    ScenarioAdapter,
    ShadowAuditFeedback,
)
from app.modules.execution_runtime.scenario_models import (  # noqa: E402
    ScenarioOracleBinding,
    TestOracle,
    TestScenario,
    TestScenarioVersion,
)
from app.modules.execution_runtime.legacy_models import LegacyObjectMapping

__all__ = [
    "AiProvider",
    "AiResponseCache",
    "AiShadowRun",
    "AiTask",
    "AiAgent",
    "AiAgentToken",
    "ModelUsageLedger",
    "PlanExecutionJob",
    "ExecutionJob",
    "ImpactEdge",
    "ReuseSuggestionEvent",
    "InteractionEdge",
    "ApiEndpoint",
    "ApiExecutionTask",
    "ApiExecutionTaskItem",
    "ApiImportBatch",
    "ApiService",
    "TestCampaign",
    "CampaignItem",
    "ApiToken",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Project",
    "ProjectMember",
    "ProjectInvite",
    "AuditLog",
    "Environment",
    "EnvironmentVariable",
    "QualityGateConfig",
    "TestCase",
    "TestCaseDomain",
    "TestCaseModule",
    "TestCaseReviewTransition",
    "TestCaseVersion",
    "TestPlan",
    "TestPlanCase",
    "TestExecution",
    "TestSchedule",
    "TestScheduleRun",
    "Defect",
    "UiTestJob",
    "UiTestRun",
    "UiTestScript",
    "RequirementDocument",
    "RequirementReview",
    "RunnerExecutionTask",
    "RequirementModule",
    "ModuleAdminLink",
    "ReleaseBundle",
    "InviteCode",
    "VersionTask",
    "VersionTaskDefect",
    "VersionTaskExecution",
    "VersionTaskPlanItem",
    "VersionTaskRun",
    "VersionKnowledgeRecord",
    "KnowledgeSource",
    "KnowledgeChunk",
    "KnowledgeEntity",
    "KnowledgeRelation",
    "KnowledgeVector",
    "WikiRawSource",
    "WikiPage",
    "WikiLink",
    "WikiIngestJob",
    "LanhuEvidenceJob",
    "LanhuEvidencePage",
    "LanhuEvidenceAsset",
    "LanhuOcrBlock",
    # execution_runtime（保留执行事实表）
    "ScenarioAdapter",
    "EnvironmentSnapshot",
    "ExecutionRun",
    "ExecutionStep",
    "AssertionResult",
    "EvidenceArtifact",
    "ReplayManifest",
    "LegacyExecutionLink",
    "ShadowAuditFeedback",
    "TestScenario",
    "TestScenarioVersion",
    "TestOracle",
    "ScenarioOracleBinding",
    "LegacyObjectMapping",
]
