"""Small, deterministic factories shared by Batch 59 acceptance tests."""
from __future__ import annotations

from app.models.project import Project
from app.models.test_case import TestCase as CaseModel
from app.models.test_plan import TestExecution as ExecutionModel
from app.models.test_plan import TestPlan as PlanModel
from app.models.test_plan import TestPlanCase as PlanCaseModel


def seed_projects(db_session) -> tuple[Project, Project, Project]:
    """Create an owned, foreign, and empty project."""
    projects = (
        Project(id=1, code="B59-A", name="Batch 59 Project A"),
        Project(id=2, code="B59-B", name="Batch 59 Project B"),
        Project(id=3, code="B59-EMPTY", name="Batch 59 Empty Project"),
    )
    db_session.add_all(projects)
    db_session.commit()
    return projects


def seed_case_plan_execution(
    db_session,
    *,
    project_id: int,
    suffix: str,
    execution_status: str = "pass",
) -> tuple[CaseModel, PlanModel, ExecutionModel]:
    case = CaseModel(
        project_id=project_id,
        case_id=f"B59-{suffix}",
        title=f"Batch 59 {suffix} case",
        priority="P0",
    )
    plan = PlanModel(
        project_id=project_id,
        plan_id=f"B59-PLAN-{suffix}",
        name=f"Batch 59 {suffix} plan",
    )
    db_session.add_all([case, plan])
    db_session.flush()
    plan_case = PlanCaseModel(
        plan_id=plan.id,
        case_id=case.id,
        last_status=execution_status,
    )
    db_session.add(plan_case)
    db_session.flush()
    execution = ExecutionModel(
        plan_case_id=plan_case.id,
        status=execution_status,
        actual_result=f"{suffix} result",
    )
    db_session.add(execution)
    db_session.commit()
    return case, plan, execution
