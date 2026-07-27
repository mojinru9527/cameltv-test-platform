"""测试报告聚合 — 统一 API 测试 + UI 自动化的执行数据。

提供项目维度的全景测试摘要，供报告中心/工作台使用。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def get_aggregated_summary(db: Session, project_id: int, *, days: int = 7) -> dict:
    """获取项目最近 N 天的测试全景摘要（API + UI）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    api_summary = _api_summary(db, project_id, cutoff)
    ui_summary = _ui_summary(db, project_id, cutoff)

    total_runs = api_summary["total_tasks"] + ui_summary["total_runs"]
    total_passed = api_summary["total_passed"] + ui_summary["total_passed"]
    total_failed = api_summary["total_failed"] + ui_summary["total_failed"]

    return {
        "period_days": days,
        "api": api_summary,
        "ui": ui_summary,
        "combined": {
            "total_runs": total_runs,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_rate": round(total_passed / max(total_passed + total_failed, 1) * 100, 1),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _api_summary(db: Session, project_id: int, cutoff: datetime) -> dict:
    """API 测试摘要。"""
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

    tasks = db.scalars(
        select(ApiExecutionTask).where(
            ApiExecutionTask.project_id == project_id,
            ApiExecutionTask.created_at >= cutoff,
        )
    ).all()

    total_tasks = len(tasks)
    total_passed = sum(t.passed or 0 for t in tasks)
    total_failed = sum(t.failed or 0 for t in tasks)

    # 最近 5 个任务的趋势
    recent_tasks = sorted(tasks, key=lambda t: t.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:5]
    trend = [
        {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status,
            "passed": t.passed or 0,
            "failed": t.failed or 0,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in recent_tasks
    ]

    # 失败原因分类
    failed_items = db.scalars(
        select(ApiExecutionTaskItem).where(
            ApiExecutionTaskItem.status == "failed",
            ApiExecutionTaskItem.task_id.in_(
                select(ApiExecutionTask.id).where(
                    ApiExecutionTask.project_id == project_id,
                    ApiExecutionTask.created_at >= cutoff,
                )
            ),
        )
    ).all()

    error_categories = _categorize_api_errors(failed_items)

    return {
        "total_tasks": total_tasks,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": round(total_passed / max(total_passed + total_failed, 1) * 100, 1),
        "error_categories": error_categories,
        "recent_trend": trend,
    }


def _ui_summary(db: Session, project_id: int, cutoff: datetime) -> dict:
    """UI 自动化摘要。"""
    from app.models.ui_test import UiTestJob, UiTestRun

    jobs = db.scalars(
        select(UiTestJob).where(
            UiTestJob.project_id == project_id,
            UiTestJob.created_at >= cutoff,
        )
    ).all()
    job_ids = [j.id for j in jobs]

    runs = []
    if job_ids:
        runs = db.scalars(
            select(UiTestRun).where(
                UiTestRun.job_id.in_(job_ids),
                UiTestRun.started_at >= cutoff,
            )
        ).all()

    total_runs = len(runs)
    import json as _json
    total_passed = 0
    total_failed = 0
    for r in runs:
        try:
            res = _json.loads(r.result) if r.result else {}
        except (_json.JSONDecodeError, TypeError):
            res = {}
        total_passed += res.get("pass_", 0)
        total_failed += res.get("fail", 0)

    # 最近 5 个运行的趋势
    recent_runs = sorted(runs, key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:5]
    trend = []
    for r in recent_runs:
        try:
            res = _json.loads(r.result) if r.result else {}
        except (_json.JSONDecodeError, TypeError):
            res = {}
        trend.append({
            "run_id": r.id,
            "job_id": r.job_id,
            "status": r.status,
            "passed": res.get("pass_", 0),
            "failed": res.get("fail", 0),
            "duration": res.get("duration", 0),
            "error_message": r.error_message[:200] if r.error_message else "",
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        })

    # UI 失败分类
    ui_errors = {}
    for r in runs:
        if r.status == "fail" and r.error_message:
            cat = _classify_ui_error(r.error_message)
            ui_errors[cat] = ui_errors.get(cat, 0) + 1

    return {
        "total_runs": total_runs,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": round(total_passed / max(total_passed + total_failed, 1) * 100, 1),
        "error_categories": ui_errors,
        "recent_trend": trend,
    }


def _categorize_api_errors(items: list) -> dict[str, int]:
    """将 API 失败项按错误类型分类。"""
    cats: dict[str, int] = {}
    for item in items:
        msg = (item.error_message or "").lower()
        if "超时" in msg or "timeout" in msg:
            cat = "timeout"
        elif "连接失败" in msg or "connect" in msg or "connection" in msg:
            cat = "connection"
        elif "断言" in msg or "assert" in msg:
            cat = "assertion"
        elif "生产环境" in msg or "confirm_prod" in msg:
            cat = "prod_protection"
        elif msg:
            cat = "other"
        else:
            cat = "unknown"
        cats[cat] = cats.get(cat, 0) + 1
    return cats


def _classify_ui_error(error_msg: str) -> str:
    """分类 UI 错误。"""
    msg = error_msg.lower()
    if "超时" in msg or "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "playwright" in msg and ("不可用" in msg or "not" in msg):
        return "playwright_unavailable"
    if "npx" in msg:
        return "npx_missing"
    if "不存在" in msg or "not found" in msg:
        return "spec_missing"
    if "取消" in msg or "cancel" in msg:
        return "cancelled"
    return "other"
