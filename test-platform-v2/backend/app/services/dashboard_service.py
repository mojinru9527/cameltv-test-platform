"""Dashboard service — aggregate project-level statistics with time-range support."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, case as sa_case
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase

# ── 用例类型 → 展示标签 + 卡片颜色 ──
CASE_TYPE_META = {
    "manual":  {"label": "功能用例", "color": "#1890ff"},
    "api":     {"label": "接口用例", "color": "#52c41a"},
    "ui":      {"label": "自动化用例", "color": "#fa8c16"},
}


def _execution_filter_for_project(db: Session, project_id: int, start: date | None, end: date | None):
    """构建执行记录的公共过滤子查询，支持时间范围。

    返回 (total_execs, pass_execs, fail_execs) 三元组，均为标量。
    """
    plan_ids_sub = (
        select(TestPlan.id).where(TestPlan.project_id == project_id).scalar_subquery()
    )
    pcase_ids_sub = (
        select(TestPlanCase.id)
        .where(TestPlanCase.plan_id.in_(plan_ids_sub))
        .scalar_subquery()
    )

    base = select(func.count(TestExecution.id)).where(
        TestExecution.plan_case_id.in_(pcase_ids_sub)
    )
    pass_base = base.where(TestExecution.status == "pass")
    fail_base = base.where(TestExecution.status == "fail")

    if start:
        start_dt = datetime.combine(start, datetime.min.time())
        base = base.where(TestExecution.executed_at >= start_dt)
        pass_base = pass_base.where(TestExecution.executed_at >= start_dt)
        fail_base = fail_base.where(TestExecution.executed_at >= start_dt)
    if end:
        end_dt = datetime.combine(end, datetime.max.time())
        base = base.where(TestExecution.executed_at <= end_dt)
        pass_base = pass_base.where(TestExecution.executed_at <= end_dt)
        fail_base = fail_base.where(TestExecution.executed_at <= end_dt)

    total = db.scalar(base) or 0
    pass_ = db.scalar(pass_base) or 0
    fail_ = db.scalar(fail_base) or 0
    return total, pass_, fail_


def get_dashboard_stats(
    db: Session,
    project_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Return aggregate statistics for the dashboard.

    用例数量始终为全量（不受时间筛选），通过率/失败率限制在时间范围内。
    """

    # ── 用例总数（全量） ──
    total_cases = db.scalar(
        select(func.count(TestCase.id)).where(TestCase.project_id == project_id)
    ) or 0

    # ── 测试计划数（全量） ──
    total_plans = db.scalar(
        select(func.count(TestPlan.id)).where(TestPlan.project_id == project_id)
    ) or 0

    # ── API 用例数（全量） ──
    api_cases = db.scalar(
        select(func.count(TestCase.id)).where(
            TestCase.project_id == project_id,
            TestCase.case_type == "api",
        )
    ) or 0

    # ── 整体通过率（受时间范围约束） ──
    total_execs, pass_execs, fail_execs = _execution_filter_for_project(
        db, project_id, start_date, end_date
    )
    pass_rate = round((pass_execs / total_execs) * 100, 1) if total_execs > 0 else 0.0

    # ── P0-P3 优先级分布（按用例类型） ──
    priority_rows = db.execute(
        select(TestCase.case_type, TestCase.priority, func.count(TestCase.id))
        .where(TestCase.project_id == project_id)
        .group_by(TestCase.case_type, TestCase.priority)
    ).all()

    # 按 case_type 聚合
    priority_map: dict[str, dict[str, int]] = {}
    for ct, pri, cnt in priority_rows:
        priority_map.setdefault(ct, {"P0": 0, "P1": 0, "P2": 0, "P3": 0})
        if pri in ("P0", "P1", "P2", "P3"):
            priority_map[ct][pri] = cnt

    priority_distribution: list[dict] = []
    for ct, meta in CASE_TYPE_META.items():
        p = priority_map.get(ct, {"P0": 0, "P1": 0, "P2": 0, "P3": 0})
        total = sum(p.values())
        priority_distribution.append({
            "case_type": ct,
            "label": meta["label"],
            "color": meta["color"],
            "p0": p["P0"],
            "p1": p["P1"],
            "p2": p["P2"],
            "p3": p["P3"],
            "total": total,
        })

    # ── 按用例类型分组统计 ──
    case_type_stats: list[dict] = []
    for ct, meta in CASE_TYPE_META.items():
        # 该类型用例总数
        ct_count = db.scalar(
            select(func.count(TestCase.id)).where(
                TestCase.project_id == project_id,
                TestCase.case_type == ct,
            )
        ) or 0

        # 该类型的执行统计（通过 plan_case → plan 关联）
        pcase_for_type = (
            select(TestPlanCase.id)
            .where(
                TestPlanCase.plan_id.in_(
                    select(TestPlan.id).where(TestPlan.project_id == project_id).scalar_subquery()
                ),
                TestPlanCase.case_id.in_(
                    select(TestCase.id).where(
                        TestCase.project_id == project_id,
                        TestCase.case_type == ct,
                    ).scalar_subquery()
                ),
            )
            .scalar_subquery()
        )

        ct_exec_base = select(func.count(TestExecution.id)).where(
            TestExecution.plan_case_id.in_(pcase_for_type)
        )
        ct_pass_base = ct_exec_base.where(TestExecution.status == "pass")
        ct_fail_base = ct_exec_base.where(TestExecution.status == "fail")

        if start_date:
            start_dt = datetime.combine(start_date, datetime.min.time())
            ct_exec_base = ct_exec_base.where(TestExecution.executed_at >= start_dt)
            ct_pass_base = ct_pass_base.where(TestExecution.executed_at >= start_dt)
            ct_fail_base = ct_fail_base.where(TestExecution.executed_at >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, datetime.max.time())
            ct_exec_base = ct_exec_base.where(TestExecution.executed_at <= end_dt)
            ct_pass_base = ct_pass_base.where(TestExecution.executed_at <= end_dt)
            ct_fail_base = ct_fail_base.where(TestExecution.executed_at <= end_dt)

        ct_exec_total = db.scalar(ct_exec_base) or 0
        ct_exec_pass = db.scalar(ct_pass_base) or 0
        ct_exec_fail = db.scalar(ct_fail_base) or 0

        ct_pass_rate = round((ct_exec_pass / ct_exec_total) * 100, 1) if ct_exec_total > 0 else 0.0
        ct_fail_rate = round((ct_exec_fail / ct_exec_total) * 100, 1) if ct_exec_total > 0 else 0.0

        case_type_stats.append({
            "case_type": ct,
            "label": meta["label"],
            "color": meta["color"],
            "count": ct_count,
            "execution_total": ct_exec_total,
            "execution_pass": ct_exec_pass,
            "execution_fail": ct_exec_fail,
            "pass_rate": ct_pass_rate,
            "fail_rate": ct_fail_rate,
        })

    # ── 时间范围信息 ──
    time_range = {
        "start": start_date.isoformat() if start_date else None,
        "end": end_date.isoformat() if end_date else None,
    }

    return {
        "total_cases": total_cases,
        "total_plans": total_plans,
        "api_cases": api_cases,
        "pass_rate": pass_rate,
        "case_type_stats": case_type_stats,
        "priority_distribution": priority_distribution,
        "time_range": time_range,
    }
