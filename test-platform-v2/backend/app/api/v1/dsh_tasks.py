"""DSH 任务执行模块 API —— /api/v1/dsh-tasks/*（Batch 172）。

提交自然语言任务，平台通过 DeepSeek Harness 后台执行，列表/详情可追溯。
权限复用 agent:view（读）/ agent:run（写）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.dsh import DshHealthOut, DshTaskCancelResponse, DshTaskCreate, DshTaskOut
from app.services.dsh import dsh_task_service
from app.services.dsh.dsh_runner import runtime_available

router = APIRouter(prefix="/dsh-tasks", tags=["DSH 任务"])


@router.get("/health", response_model=R[DshHealthOut], summary="DSH 运行可用性")
def dsh_health(
    current: CurrentUser = Depends(require_permission("agent:view")),
):
    ok, reason = runtime_available()
    return R.ok(DshHealthOut(available=ok, reason=reason))


@router.post("", response_model=R[DshTaskOut], summary="提交 DSH 任务")
def create_dsh_task(
    body: DshTaskCreate,
    current: CurrentUser = Depends(require_permission("agent:run")),
    db: Session = Depends(get_db),
):
    ok, reason = runtime_available()
    if not ok:
        return R(code=503, msg=f"DSH 不可用: {reason}")
    # DSH 测试 Agent 框架（阶段 3）：模型池准入——配置了池则只允许池内模型
    model = (body.params or {}).get("model")
    if model and not settings.dsh_model_allowed(model):
        return R(code=400, msg=f"模型不在可用模型池内: {model}（可选: {', '.join(settings.dsh_model_pool_list) or '未配置池'}）")
    row = dsh_task_service.submit_task(
        db,
        project_id=current.project_id or 0,
        task=body.task,
        params=body.params,
        mode=body.mode,
        operator_id=current.user.id,
    )
    return R.ok(DshTaskOut.model_validate(row))


@router.get("", response_model=R[Page[DshTaskOut]], summary="DSH 任务列表")
def list_dsh_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("agent:view")),
    db: Session = Depends(get_db),
):
    rows, total = dsh_task_service.list_tasks(
        db,
        current.project_id or 0,
        status=status,
        page=page,
        page_size=page_size,
    )
    return R.ok(Page(
        total=total,
        page=page,
        page_size=page_size,
        items=[DshTaskOut.model_validate(r) for r in rows],
    ))


@router.get("/{task_id}", response_model=R[DshTaskOut], summary="DSH 任务详情")
def get_dsh_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("agent:view")),
    db: Session = Depends(get_db),
):
    row = dsh_task_service.get_task(db, task_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="DSH 任务不存在")
    return R.ok(DshTaskOut.model_validate(row))


@router.post("/{task_id}/cancel", response_model=R[DshTaskCancelResponse], summary="取消 DSH 任务")
def cancel_dsh_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("agent:run")),
    db: Session = Depends(get_db),
):
    row = dsh_task_service.cancel_task(db, task_id, current.project_id or 0)
    if row is None:
        return R(code=404, msg="任务不存在或不可取消（仅 pending 可取消）")
    return R.ok(DshTaskCancelResponse(id=row.id, status=row.status, message="任务已取消"))
