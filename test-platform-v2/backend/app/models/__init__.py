"""统一导出所有模型，确保 Base.metadata 能感知全部表。"""
from app.models.ai_provider import AiProvider
from app.models.ai_task import AiTask
from app.models.interaction_edge import InteractionEdge
from app.models.api_asset import ApiEndpoint, ApiExecutionTask, ApiExecutionTaskItem, ApiImportBatch, ApiService
from app.models.api_token import ApiToken
from app.models.audit import AuditLog
from app.models.dataset import Dataset
from app.models.dsh_task import DshTask
from app.models.defect import Defect
from app.models.environment import Environment, EnvironmentVariable
from app.models.integration import IntegrationConfig
from app.models.invite_code import InviteCode
from app.models.lanhu_evidence import (
    LanhuEvidenceAsset,
    LanhuEvidenceJob,
    LanhuEvidencePage,
    LanhuOcrBlock,
)
from app.models.knowledge import (
    AgentQueueItem,
    AgentRun,
    AiArtifact,
    KnowledgeChunk,
    KnowledgeEntity,
    KnowledgeIteration,
    KnowledgeRelation,
    KnowledgeSnapshot,
    KnowledgeSource,
    KnowledgeVector,
)
from app.models.project import Project, ProjectMember
from app.models.project_invite import ProjectInvite
from app.models.notification import NotificationChannel, NotificationLog
from app.models.organization import Organization, OrganizationMember
from app.models.production_evidence import (
    EntityGraphSnapshot,
    MaskingProfile,
    MaskingRule,
    ObservedJourney,
    ObservedJourneyStep,
    ProdDataTemplate,
    ProductionObservationSession,
    ProductionQueryAudit,
    TemplateMaterialization,
)
from app.models.quality_gate import QualityGateConfig
from app.models.report_template import ReportTemplate
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.requirement_review import RequirementReview
from app.models.runner_execution import RunnerExecutionTask
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.sync_log import SyncLog
from app.models.test_case import TestCase
from app.models.test_case_category import TestCaseDomain, TestCaseModule
from app.models.test_case_review import TestCaseReviewTransition
from app.models.test_case_version import TestCaseVersion
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_report import TestReport
from app.models.test_schedule import TestSchedule, TestScheduleRun
from app.models.ui_test import UiTestJob, UiTestRun, UiTestScript
from app.models.user import User
from app.models.version_mission import AgentWorkLog, GeneratedArtifact, VersionMission
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.models.version_task_plan import VersionTaskPlanItem
from app.models.wiki import (
    ExternalWikiConnection,
    WikiDiffItem,
    WikiDiffTask,
    WikiIngestJob,
    WikiLink,
    WikiLintIssue,
    WikiLintReport,
    WikiPage,
    WikiRawSource,
    WikiReviewContradiction,
    WikiReviewItem,
)

__all__ = [
    "AiProvider",
    "AiTask",
    "InteractionEdge",
    "ApiEndpoint",
    "ApiExecutionTask",
    "ApiExecutionTaskItem",
    "ApiImportBatch",
    "ApiService",
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
    "NotificationChannel",
    "NotificationLog",
    "Organization",
    "OrganizationMember",
    "ProductionObservationSession",
    "ObservedJourney",
    "ObservedJourneyStep",
    "ProductionQueryAudit",
    "MaskingProfile",
    "MaskingRule",
    "EntityGraphSnapshot",
    "ProdDataTemplate",
    "TemplateMaterialization",
    "QualityGateConfig",
    "ReportTemplate",
    "TestCase",
    "TestCaseDomain",
    "TestCaseModule",
    "TestCaseReviewTransition",
    "TestCaseVersion",
    "TestPlan",
    "TestPlanCase",
    "TestExecution",
    "TestReport",
    "TestSchedule",
    "TestScheduleRun",
    "Dataset",
    "DshTask",
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
    "IntegrationConfig",
    "InviteCode",
    "SyncLog",

    "VersionMission",
    "VersionTask",
    "VersionTaskDefect",

    "VersionTaskExecution",
    "VersionTaskPlanItem",
    "AgentWorkLog",
    "GeneratedArtifact",
    "KnowledgeSource",
    "KnowledgeChunk",
    "KnowledgeEntity",
    "KnowledgeRelation",
    "KnowledgeVector",
    "AiArtifact",
    "AgentRun",
    "AgentQueueItem",
    "KnowledgeIteration",
    "KnowledgeSnapshot",
    "WikiRawSource",
    "WikiPage",
    "WikiLink",
    "WikiIngestJob",
    "WikiDiffTask",
    "WikiDiffItem",
    "WikiReviewItem",
    "WikiReviewContradiction",
    "ExternalWikiConnection",
    "WikiLintReport",
    "WikiLintIssue",
    "LanhuEvidenceJob",
    "LanhuEvidencePage",
    "LanhuEvidenceAsset",
    "LanhuOcrBlock",
]



