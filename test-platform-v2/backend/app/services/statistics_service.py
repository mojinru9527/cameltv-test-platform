"""统计口径统一服务（Batch 149 / C147-3）— 用例域唯一统计源。

口径定义（与 work-logs/batch-149-* 工件一致）：
- 用例总数 / 类型分布：TestCase.project_id 且 is_deleted=False
- 执行计数：TestExecution 经 plan_case → plan 归属项目，**不因用例删除而丢失**（保留真实执行）
- 已执行 / 已通过用例：distinct plan_case.case_id，且用例 is_deleted=False
- 计划内用例：distinct plan_case.case_id，且用例 is_deleted=False
- 时间筛选只作用于执行计数，用例/计划数为全量
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.services.test_case_service import canonical_case_type, case_type_values

CASE_TYPES: tuple[str, ...] = ("manual", "api", "ui")


def _active_cases_sub(project_id: int):
    """当前项目未删除用例 id 子查询。"""
    return (
        select(TestCase.id)
        .where(TestCase.project_id == project_id, TestCase.is_deleted.is_(False))
        .scalar_subquery()
    )


def _execution_filter(
    db: Session,
    *,
    project_id: int,
    plan_case_ids_sub=None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[int, int, int]:
    """统计 TestExecution 总数/通过/失败（可附加 plan_case 子查询与时间范围）。"""
    if plan_case_ids_sub is not None:
        plan_case_ids = plan_case_ids_sub
    else:
        plan_case_ids = (
            select(TestPlanCase.id)
            .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
            .where(TestPlan.project_id == project_id)
            .scalar_subquery()
        )
    # Batch 158 热修：必须用 IN (subquery) 包装，否则 PG 报
    # "argument of WHERE must be type boolean, not type integer"（SQLite 宽松不报）
    base = select(func.count(TestExecution.id)).where(
        TestExecution.plan_case_id.in_(plan_case_ids)
    )
    pass_base = base.where(TestExecution.status == "pass")
    fail_base = base.where(TestExecution.status == "fail")

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        base = base.where(TestExecution.executed_at >= start_dt)
        pass_base = pass_base.where(TestExecution.executed_at >= start_dt)
        fail_base = fail_base.where(TestExecution.executed_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        base = base.where(TestExecution.executed_at <= end_dt)
        pass_base = pass_base.where(TestExecution.executed_at <= end_dt)
        fail_base = fail_base.where(TestExecution.executed_at <= end_dt)

    return (db.scalar(base) or 0, db.scalar(pass_base) or 0, db.scalar(fail_base) or 0)


def get_project_statistics(
    db: Session,
    project_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """项目级统计（用例域统一口径）。"""
    active = _active_cases_sub(project_id)

    total_cases = db.scalar(
        select(func.count(TestCase.id)).where(
            TestCase.project_id == project_id, TestCase.is_deleted.is_(False)
        )
    ) or 0

    api_cases = db.scalar(
        select(func.count(TestCase.id)).where(
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestCase.case_type.in_(case_type_values("api")),
        )
    ) or 0

    total_plans = db.scalar(
        select(func.count(TestPlan.id)).where(TestPlan.project_id == project_id)
    ) or 0

    # 执行计数（不因用例删除丢失）
    exec_total, exec_pass, exec_fail = _execution_filter(
        db, project_id=project_id, start_date=start_date, end_date=end_date
    )

    # 用例级：计划内 / 已执行 / 已通过（仅未删除用例）
    plan_case_ids = (
        select(TestPlanCase.id)
        .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
        .where(TestPlan.project_id == project_id)
    )
    cases_in_plans = db.scalar(
        select(func.count())
        .select_from(
            select(TestPlanCase.case_id)
            .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
            .where(TestPlan.project_id == project_id, TestPlanCase.case_id.in_(active))
            .distinct()
            .subquery()
        )
    ) or 0

    executed_case_ids = (
        select(TestPlanCase.case_id)
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
        .where(TestPlan.project_id == project_id, TestPlanCase.case_id.in_(active))
        .distinct()
    )
    cases_executed = db.scalar(
        select(func.count()).select_from(executed_case_ids.subquery())
    ) or 0

    passed_case_ids = executed_case_ids.where(TestExecution.status == "pass")
    cases_passed = db.scalar(
        select(func.count()).select_from(passed_case_ids.subquery())
    ) or 0

    # 分类型：用例数（未删除）+ 执行计数（不过滤删除，保留真实执行）
    by_type: dict[str, dict] = {}
    for ct in CASE_TYPES:
        ct_count = db.scalar(
            select(func.count(TestCase.id)).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                TestCase.case_type.in_(case_type_values(ct)),
            )
        ) or 0
        ct_pcase_ids = (
            select(TestPlanCase.id)
            .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
            .where(
                TestPlan.project_id == project_id,
                TestPlanCase.case_id.in_(
                    select(TestCase.id)
                    .where(
                        TestCase.project_id == project_id,
                        TestCase.case_type.in_(case_type_values(ct)),
                    )
                    .scalar_subquery()
                ),
            )
            .scalar_subquery()
        )
        ct_exec_total, ct_exec_pass, ct_exec_fail = _execution_filter(
            db,
            project_id=project_id,
            plan_case_ids_sub=ct_pcase_ids,
            start_date=start_date,
            end_date=end_date,
        )
        by_type[ct] = {
            "count": ct_count,
            "execution_total": ct_exec_total,
            "execution_pass": ct_exec_pass,
            "execution_fail": ct_exec_fail,
        }

    return {
        "total_cases": total_cases,
        "api_cases": api_cases,
        "total_plans": total_plans,
        "execution_total": exec_total,
        "execution_pass": exec_pass,
        "execution_fail": exec_fail,
        "cases_in_plans": cases_in_plans,
        "cases_executed": cases_executed,
        "cases_passed": cases_passed,
        "by_type": by_type,
        "coverage_rate": round(cases_in_plans / total_cases * 100, 1) if total_cases else 0.0,
        "execution_rate": round(cases_executed / total_cases * 100, 1) if total_cases else 0.0,
        "pass_rate": round(cases_passed / max(cases_executed, 1) * 100, 1),
    }
