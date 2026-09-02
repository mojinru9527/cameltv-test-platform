"""Dashboard service — aggregate project-level statistics with time-range support."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.services import statistics_service
from app.models.ai_task import AiTask
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_review import RequirementReview
from app.services.test_case_service import canonical_case_type

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
    pass_base = base.where(TestExecution.status == "passed")
    fail_base = base.where(TestExecution.status == "failed")

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

    # ── 统一口径统计（Batch 149 / C147-3：statistics_service 为唯一事实源） ──
    st = statistics_service.get_project_statistics(
        db, project_id, start_date=start_date, end_date=end_date,
    )
    total_cases = st["total_cases"]
    total_plans = st["total_plans"]
    api_cases = st["api_cases"]
    total_execs = st["execution_total"]
    pass_execs = st["execution_pass"]
    fail_execs = st["execution_fail"]
    # Batch 175（FIX-173-P1-01）：通过率统一为「用例级」口径（cases_passed / cases_executed），
    # 与质量追溯/报告中心一致，消除工作台 9.1% vs 追溯 22.1% 的分裂。
    # 执行记录级通过率（含重跑）作为独立字段保留，供明细/趋势展示并明确标注口径。
    pass_rate = st["pass_rate"]
    execution_pass_rate = round((pass_execs / total_execs) * 100, 1) if total_execs > 0 else 0.0

    # ── P0-P3 优先级分布（按用例类型） ──
    priority_rows = db.execute(
        select(TestCase.case_type, TestCase.priority, func.count(TestCase.id))
        .where(TestCase.project_id == project_id, TestCase.is_deleted.is_(False))
        .group_by(TestCase.case_type, TestCase.priority)
    ).all()

    # 按 case_type 聚合
    priority_map: dict[str, dict[str, int]] = {}
    for ct, pri, cnt in priority_rows:
        ct = canonical_case_type(ct)
        priority_map.setdefault(ct, {"P0": 0, "P1": 0, "P2": 0, "P3": 0})
        if pri in ("P0", "P1", "P2", "P3"):
            priority_map[ct][pri] += cnt

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

    # ── 按用例类型分组统计（统一口径 statistics_service） ──
    case_type_stats: list[dict] = []
    for ct, meta in CASE_TYPE_META.items():
        b = st["by_type"].get(ct, {"count": 0, "execution_total": 0, "execution_pass": 0, "execution_fail": 0})
        ct_count = b["count"]
        ct_exec_total = b["execution_total"]
        ct_exec_pass = b["execution_pass"]
        ct_exec_fail = b["execution_fail"]

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
            "execution_pass_rate": ct_pass_rate,  # 兼容：类型级仅有执行记录口径
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
        "execution_pass_rate": execution_pass_rate,
        "case_type_stats": case_type_stats,
        "priority_distribution": priority_distribution,
        "time_range": time_range,
    }


# ── V2.5: Cross-project aggregation ──

def get_cross_project_stats(
    db: Session,
    user_id: int,
    is_superadmin: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Aggregate dashboard statistics across all projects visible to the user."""
    from app.services import project_service

    projects = project_service.projects_for_user(db, user_id, is_superadmin)
    project_ids = [p.id for p in projects]
    project_list = [{"id": p.id, "code": p.code, "name": p.name} for p in projects]

    if not project_ids:
        return {
            "projects": [],
            "aggregate": {
                "total_projects": 0, "total_cases": 0, "total_plans": 0,
                "total_api_cases": 0, "overall_pass_rate": 0.0, "total_defects": 0,
            },
            "per_project": [],
            "trends": {"pass_rate": [], "defects": []},
        }

    # Per-project stats
    per_project = []
    agg_cases = 0
    agg_plans = 0
    agg_execs = 0
    agg_pass = 0
    agg_defects = 0

    for pid in project_ids:
        stats = get_dashboard_stats(db, pid, start_date, end_date)
        defect_count = db.scalar(
            select(func.count(Defect.id)).where(Defect.project_id == pid)
        ) or 0

        per_project.append({
            "project_id": pid,
            "project_name": next((p["name"] for p in project_list if p["id"] == pid), ""),
            "total_cases": stats["total_cases"],
            "total_plans": stats["total_plans"],
            "api_cases": stats["api_cases"],
            "pass_rate": stats["pass_rate"],
            "defect_count": defect_count,
        })
        agg_cases += stats["total_cases"]
        agg_plans += stats["total_plans"]
        agg_defects += defect_count
        total, pass_, _ = _execution_filter_for_project(db, pid, start_date, end_date)
        agg_execs += total
        agg_pass += pass_

    overall_pr = round((agg_pass / agg_execs) * 100, 1) if agg_execs > 0 else 0.0

    aggregate = {
        "total_projects": len(project_ids),
        "total_cases": agg_cases,
        "total_plans": agg_plans,
        "total_api_cases": sum(p["api_cases"] for p in per_project),
        "overall_pass_rate": overall_pr,
        "total_defects": agg_defects,
    }

    # Trends: last 7 days
    pass_rate_trend = []
    defect_trend = []
    today = date.today()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_execs = 0
        day_pass = 0
        day_defects = 0
        for pid in project_ids:
            t, p, _ = _execution_filter_for_project(db, pid, day, day)
            day_execs += t
            day_pass += p
            dc = db.scalar(
                select(func.count(Defect.id)).where(
                    Defect.project_id == pid,
                    Defect.created_at >= datetime.combine(day, datetime.min.time()),
                    Defect.created_at <= datetime.combine(day, datetime.max.time()),
                )
            ) or 0
            day_defects += dc
        day_pr = round((day_pass / day_execs) * 100, 1) if day_execs > 0 else 0.0
        pass_rate_trend.append({"date": day.isoformat(), "pass_rate": day_pr, "total_execs": day_execs, "count": None})
        defect_trend.append({"date": day.isoformat(), "pass_rate": None, "total_execs": None, "count": day_defects})

    return {
        "projects": project_list,
        "aggregate": aggregate,
        "per_project": per_project,
        "trends": {"pass_rate": pass_rate_trend, "defects": defect_trend},
    }



# ── Batch 213 (B3): 首页「我的待办」聚合 ──

def _todo_bucket(items: list[dict], count: int) -> dict:
    return {"count": count, "items": items}


def get_todo_items(db: Session, project_id: int) -> dict:
    """首页「我的待办」聚合：待审/在跑/失败/待放行。

    - project_id > 0：仅统计该项目；== 0：不按项目过滤（兼顾超级管理员全量视角）。
    - 各桶 max 5 条 items，count 为总数；空桶返回 count=0、items=[]。
    """
    project_cond = lambda col: (col == project_id) if project_id > 0 else True  # noqa: E731

    # 待审：AI 生成候选用例待审（RequirementReview.status=pending）
    review_q = (
        select(RequirementReview, RequirementDocument.title)
        .join(RequirementDocument, RequirementReview.requirement_id == RequirementDocument.id)
        .where(RequirementReview.status == "pending", project_cond(RequirementDocument.project_id))
    )
    review_rows = db.execute(review_q.order_by(RequirementReview.id.desc()).limit(5)).all()
    reviews_items = [
        {
            "id": f"review-{req.id}",
            "title": title or f"需求 #{req.requirement_id}",
            "subtitle": f"{req.case_type} 用例 待审",
            "link": f"/requirement/{req.requirement_id}/review",
        }
        for req, title in review_rows
    ]
    reviews_count = db.scalar(
        select(func.count(RequirementReview.id))
        .join(RequirementDocument, RequirementReview.requirement_id == RequirementDocument.id)
        .where(RequirementReview.status == "pending", project_cond(RequirementDocument.project_id))
    ) or 0

    # 在跑：后台 AI 任务 running
    running_rows = db.execute(
        select(AiTask)
        .where(AiTask.status == "running", project_cond(AiTask.project_id))
        .order_by(AiTask.id.desc()).limit(5)
    ).scalars().all()
    running_items = [
        {
            "id": task.id,
            "title": f"{task.task_type} 任务",
            "subtitle": f"进度 {task.progress}%",
            "link": "/report",
        }
        for task in running_rows
    ]
    running_count = db.scalar(
        select(func.count(AiTask.id)).where(AiTask.status == "running", project_cond(AiTask.project_id))
    ) or 0

    # 失败：AI 任务 failed + 未关闭缺陷
    failed_task_rows = db.execute(
        select(AiTask)
        .where(AiTask.status == "failed", project_cond(AiTask.project_id))
        .order_by(AiTask.id.desc()).limit(5)
    ).scalars().all()
    defect_rows = db.execute(
        select(Defect)
        .where(Defect.status.notin_(["closed", "rejected"]), project_cond(Defect.project_id))
        .order_by(Defect.id.desc()).limit(5)
    ).scalars().all()
    failures_items: list[dict] = []
    for task in failed_task_rows:
        failures_items.append({
            "id": f"task-{task.id}",
            "title": f"{task.task_type} 任务失败",
            "subtitle": task.error or "执行失败",
            "link": "/report",
        })
    for d in defect_rows:
        failures_items.append({
            "id": f"defect-{d.id}",
            "title": d.title or f"缺陷 #{d.id}",
            "subtitle": f"严重级 {d.severity}",
            "link": f"/defect/{d.id}",
        })
    failures_items = failures_items[:5]
    failed_task_count = db.scalar(
        select(func.count(AiTask.id)).where(AiTask.status == "failed", project_cond(AiTask.project_id))
    ) or 0
    defect_count = db.scalar(
        select(func.count(Defect.id)).where(
            Defect.status.notin_(["closed", "rejected"]),
            project_cond(Defect.project_id),
        )
    ) or 0
    failures_count = failed_task_count + defect_count

    # 待放行：当前版本发布包（active）
    release_rows = db.execute(
        select(ReleaseBundle)
        .where(ReleaseBundle.status == "active", project_cond(ReleaseBundle.project_id))
        .order_by(ReleaseBundle.id.desc()).limit(5)
    ).scalars().all()
    release_items = [
        {
            "id": f"release-{b.id}",
            "title": b.name or f"发布包 #{b.id}",
            "subtitle": (b.client_version or "") + ((" / " + b.admin_version) if b.admin_version else ""),
            "link": f"/release-bundles/{b.id}",
        }
        for b in release_rows
    ]
    release_count = db.scalar(
        select(func.count(ReleaseBundle.id)).where(
            ReleaseBundle.status == "active",
            project_cond(ReleaseBundle.project_id),
        )
    ) or 0

    return {
        "reviews": _todo_bucket(reviews_items, reviews_count),
        "running": _todo_bucket(running_items, running_count),
        "failures": _todo_bucket(failures_items, failures_count),
        "releases": _todo_bucket(release_items, release_count),
    }

