"""接口测试 API 路由（任务域） —— /api/v1/apitest/*

Batch 181（FIX-173-P2-10）路由拆分：即时执行 / 批量任务 / 任务结果。
端点函数体与原 apitest.py 逐字一致；ApiExecutionTask/ApiExecutionTaskItem/
TestCase ORM 查询收敛到 app.services.api_execution_service /
api_case_generation_service。
"""

from __future__ import annotations

import json
import logging
from app.modules.campaign_execution.service import create_api_task_campaign

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.api_asset import (
    ApiExecutionRequest,
    ApiTaskCreateRequest,
    ApiTaskDetailOut,
    ApiTaskItemOut,
    ApiTaskOut,
)
from app.schemas.common import R
from app.services import api_execution_service
from app.services.api_case_generation_service import get_api_cases_by_ids
from app.services.api_execution_service import build_curl_command, quick_execute
from app.services.failure_analyzer import analyze_api_failure
from app.services.production_operation_guard import ProductionOperation, require_allowed_operation

router = APIRouter(prefix="/apitest", tags=["接口测试-任务"])


def _current_project_id(current: CurrentUser) -> int:
    """Derive current project from JWT token. Rejects missing project context."""
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


_LEGACY_MUTATION_MESSAGE = (
    "Legacy execution history is read-only. Use canonical ExecutionRun under "
    "/api/v1/execution for new execution, retry, cancel, or report operations."
)


def _legacy_mutation_gone() -> None:
    """Fail closed before any legacy execution row can be mutated."""
    raise HTTPException(status_code=410, detail=_LEGACY_MUTATION_MESSAGE)


# ═══════════════════════════════════════════════════════
# 即时执行（保留原有功能）
# ═══════════════════════════════════════════════════════


@router.post("/api-execute", response_model=R[dict], summary="即时执行（调试）")
def api_quick_execute(
    body: ApiExecutionRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """发送一个接口请求并返回响应+断言结果（不保存为用例）。

    生产环境写操作需要 apitest:execute_prod 权限 + confirm_prod=true。
    """
    if body.source not in {"quick", "asset"} or body.request is None:
        raise HTTPException(422, "quick/asset 执行必须提供 request 定义")

    request_def = body.request.model_dump(exclude={"assertions"})
    assertions = body.request.assertions

    pid = _current_project_id(current)
    has_execute_prod = current.is_super or "apitest:execute_prod" in current.permissions
    if body.environment_id is not None:
        require_allowed_operation(
            db,
            ProductionOperation(
                action=f"Execute API {body.source} request ({body.request.method})",
                project_id=pid,
                environment_id=body.environment_id,
                permission=(
                    "apitest:execute_prod" if body.request.method in {"POST", "PUT", "PATCH", "DELETE"} else ""
                ),
                confirmed=body.confirm_prod,
            ),
            set(current.permissions),
            user_id=current.user.id,
        )

    try:
        result = quick_execute(
            db,
            request_def,
            assertions=assertions,
            project_id=pid,
            environment_id=body.environment_id,
            dataset_id=body.dataset_id,
            confirm_prod=body.confirm_prod,
            has_execute_prod=has_execute_prod,
            actor_user_id=current.user.id,
        )
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


# ═══════════════════════════════════════════════════════
# 批量执行任务
# ═══════════════════════════════════════════════════════


@router.post("/tasks", response_model=R[dict], summary="创建执行任务")
def create_task(
    body: ApiTaskCreateRequest,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从用例列表创建批量执行任务。

    对已迁移的 API 用例创建 canonical Campaign，并返回 campaign_id + run_ids。

    生产环境任务需要 apitest:execute_prod 权限 + confirm_prod=true。
    """
    pid = _current_project_id(current)

    # 验证用例存在且为 API 类型
    cases = get_api_cases_by_ids(db, pid, body.case_ids)

    if len(cases) != len(body.case_ids):
        raise HTTPException(400, "部分用例不存在或不是 API 类型")

    if body.environment_id is not None:
        has_write_case = any((case.api_method or "GET").upper() in {"POST", "PUT", "PATCH", "DELETE"} for case in cases)
        try:
            require_allowed_operation(
                db,
                ProductionOperation(
                    action=f"Create API execution campaign ({len(cases)} cases)",
                    project_id=pid,
                    environment_id=body.environment_id,
                    permission="apitest:execute_prod" if has_write_case else "",
                    confirmed=body.confirm_prod,
                ),
                set(current.permissions),
                user_id=current.user.id,
            )
        except APIException as exc:
            raise HTTPException(exc.http_status, exc.msg) from exc

    campaign, runs = create_api_task_campaign(
        db,
        project_id=pid,
        user_id=current.user.id,
        name=body.name,
        cases=cases,
        environment_id=body.environment_id,
    )
    return R.ok(
        {
            "campaign_id": campaign.id,
            "run_ids": [run.id for run in runs],
            "status": campaign.status,
            "total": len(cases),
        }
    )


@router.get("/tasks", response_model=R[dict], summary="任务列表")
def list_tasks(
    service_id: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    rows, total = api_execution_service.list_project_tasks(
        db,
        pid,
        service_id=service_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return R.ok(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [ApiTaskOut.model_validate(r) for r in rows],
        }
    )


@router.get("/tasks/{task_id}", response_model=R[ApiTaskDetailOut], summary="任务详情")
def get_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    task = api_execution_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    pid = _current_project_id(current)
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")

    items = api_execution_service.list_task_items(db, task.id)
    detail = ApiTaskDetailOut(
        **ApiTaskOut.model_validate(task).model_dump(),
        items=[ApiTaskItemOut.model_validate(it) for it in items],
    )
    return R.ok(detail)


@router.delete("/tasks/{task_id}", response_model=R[dict], summary="删除执行任务（历史只读）")
def delete_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """Historical legacy tasks are immutable; canonical runs own deletion semantics."""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")
    _legacy_mutation_gone()


@router.post("/tasks/{task_id}/cancel", response_model=R[dict], summary="取消任务（历史只读）")
def cancel_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """Historical legacy tasks cannot be cancelled; use the canonical run endpoint."""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")
    _legacy_mutation_gone()


@router.post("/tasks/{task_id}/retry-failed", response_model=R[dict], summary="重跑失败用例（历史只读）")
def retry_failed(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """Historical retry is disabled; create a canonical campaign/run instead."""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")
    _legacy_mutation_gone()


@router.get("/tasks/{task_id}/items/{item_id}/curl", response_model=R[dict], summary="生成 curl 复现命令")
def get_curl_command(
    task_id: int,
    item_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从请求快照生成等效 curl 命令，方便失败排查和复现。"""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")

    item = api_execution_service.get_task_item(db, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(404, "任务明细不存在")

    try:
        snapshot = json.loads(item.request_snapshot) if item.request_snapshot else {}
    except (json.JSONDecodeError, TypeError):
        snapshot = {}

    if not snapshot:
        raise HTTPException(400, "该执行记录无请求快照，无法生成 curl 命令")

    curl_cmd = build_curl_command(snapshot)
    return R.ok({"curl": curl_cmd, "snapshot": snapshot})


@router.get("/tasks/{task_id}/analysis", response_model=R[dict], summary="任务失败分析")
def analyze_task_failures(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """对任务中所有失败项进行结构化分析，返回分类和修复建议。"""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")

    failed_items = api_execution_service.list_failed_task_items(db, task.id)

    if not failed_items:
        return R.ok({"analyses": [], "summary": "没有失败项需要分析"})

    analyses = [analyze_api_failure(item) for item in failed_items]

    # 汇总分类
    categories: dict[str, int] = {}
    for a in analyses:
        cat = a["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return R.ok(
        {
            "total_failed": len(failed_items),
            "categories": categories,
            "analyses": analyses,
        }
    )
