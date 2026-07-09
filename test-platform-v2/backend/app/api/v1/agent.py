"""Agent 执行记录 API —— /api/v1/agents/*

本期（M0）：仅提供执行记录只读查询，建立可追踪基础设施。
真正的 Agent 触发端点（requirement/impact/case_generation 等）留 M4。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.knowledge import AgentRunOut
from app.services.knowledge import agent_run_service

router = APIRouter(prefix="/agents", tags=["Agent 工作台"])


@router.get("/runs", response_model=R[Page[AgentRunOut]], summary="Agent 执行记录列表")
def list_runs(
    agent_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("agent:list")),
    db: Session = Depends(get_db),
):
    rows, total = agent_run_service.list_runs(
        db, current.project_id or 0,
        agent_type=agent_type, status=status, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[AgentRunOut.model_validate(r) for r in rows],
    ))


@router.get("/runs/{run_id}", response_model=R[AgentRunOut], summary="Agent 执行记录详情")
def get_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("agent:list")),
    db: Session = Depends(get_db),
):
    row = agent_run_service.get_run(db, run_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="Agent 执行记录不存在")
    return R.ok(AgentRunOut.model_validate(row))
