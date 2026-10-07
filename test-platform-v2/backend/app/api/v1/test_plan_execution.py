"""测试计划 API 路由（执行记录只读面） — /api/v1/test-plans/*

平台简化批次：旧测试计划写入口（执行/批量执行/triage/缺陷草稿）已删除，
仅保留执行历史只读查询（工作台统计与缺陷追溯的数据底座）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.test_plan import ExecutionOut
from app.services import test_plan_service

router = APIRouter(prefix="/test-plans", tags=["测试计划-执行"])


@router.get("/{plan_id}/executions", response_model=R[Page[ExecutionOut]])
def list_executions(
    plan_id: int,
    pcase_id: int = 0,
    page: int = 1,
    page_size: int = 50,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    items, total = test_plan_service.get_executions(
        db,
        plan_id,
        pcase_id=pcase_id,
        page=page,
        page_size=page_size,
        project_id=current.project_id or 0,
    )
    return R.ok(Page(total=total, page=page, page_size=page_size, items=[ExecutionOut(**it) for it in items]))


@router.get("/{plan_id}/execution-jobs", response_model=R[list[dict]])
def list_execution_jobs(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    """Read historical plan jobs without restoring the legacy executor."""
    from app.services.plan_execution_history import list_jobs

    return R.ok(list_jobs(db, plan_id, current.project_id or 0))
