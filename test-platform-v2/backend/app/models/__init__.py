"""统一导出所有模型，确保 Base.metadata 能感知全部表。"""
from app.models.audit import AuditLog
from app.models.av_check import AvCheckMetric, AvCheckTask
from app.models.defect import Defect
from app.models.project import Project, ProjectMember
from app.models.notification import NotificationChannel, NotificationLog
from app.models.requirement import RequirementDocument
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_report import TestReport
from app.models.test_schedule import TestSchedule, TestScheduleRun
from app.models.ui_test import UiTestJob, UiTestRun
from app.models.user import User

__all__ = [
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Project",
    "ProjectMember",
    "AuditLog",
    "NotificationChannel",
    "NotificationLog",
    "TestCase",
    "TestPlan",
    "TestPlanCase",
    "TestExecution",
    "TestReport",
    "TestSchedule",
    "TestScheduleRun",
    "Defect",
    "AvCheckTask",
    "AvCheckMetric",
    "UiTestJob",
    "UiTestRun",
    "RequirementDocument",
]
