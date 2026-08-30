"""接口测试 API 路由（任务域） —— /api/v1/apitest/*

Batch 181（FIX-173-P2-10）路由拆分：即时执行 / 批量任务 / 任务结果。
端点函数体与原 apitest.py 逐字一致；ApiExecutionTask/ApiExecutionTaskItem/
TestCase ORM 查询收敛到 app.services.api_execution_service /
api_case_generation_service。
"""
from __future__ import annotations

import json
import logging
import uuid

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
from app.services import api_execution_service, api_task_worker
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
                    "apitest:execute_prod"
                    if body.request.method in {"POST", "PUT", "PATCH", "DELETE"}
                    else ""
                ),
                confirmed=body.confirm_prod,
            ),
            set(current.permissions),
        )

    try:
        result = quick_execute(
            db, request_def,
            assertions=assertions,
            project_id=pid,
            environment_id=body.environment_id,
            dataset_id=body.dataset_id,
            confirm_prod=body.confirm_prod,
            has_execute_prod=has_execute_prod,
        )
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


# ═══════════════════════════════════════════════════════
# 批量执行任务
# ═══════════════════════════════════════════════════════

@router.post("/tasks", response_model=R[ApiTaskOut], summary="创建执行任务")
def create_task(
    body: ApiTaskCreateRequest,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从用例列表创建批量执行任务。

    任务创建后状态为 pending，由持久化 task_worker 后台轮询认领执行。
    接口立即返回，不等待用例执行完成。

    生产环境任务需要 apitest:execute_prod 权限 + confirm_prod=true。
    """
    pid = _current_project_id(current)
    task_id_str = f"API-{uuid.uuid4().hex[:8].upper()}"

    # 验证用例存在且为 API 类型
    cases = get_api_cases_by_ids(db, pid, body.case_ids)

    if len(cases) != len(body.case_ids):
        raise HTTPException(400, "部分用例不存在或不是 API 类型")

    has_execute_prod = current.is_super or "apitest:execute_prod" in current.permissions
    if body.environment_id is not None:
        has_write_case = any(
            (case.api_method or "GET").upper() in {"POST", "PUT", "PATCH", "DELETE"}
            for case in cases
        )
        try:
            require_allowed_operation(
                db,
                ProductionOperation(
                    action=f"Create API execution task ({len(cases)} cases)",
                    project_id=pid,
                    environment_id=body.environment_id,
                    permission="apitest:execute_prod" if has_write_case else "",
                    confirmed=body.confirm_prod,
                ),
                set(current.permissions),
            )
        except APIException as exc:
            raise HTTPException(exc.http_status, exc.msg) from exc

    task = api_execution_service.create_execution_task(
        db,
        project_id=pid,
        task_id=task_id_str,
        name=body.name,
        environment_id=body.environment_id,
        service_id=body.service_id,
        status="pending",
        total=len(cases),
        creator_id=current.user.id if current.user else 0,
        confirm_prod=body.confirm_prod,
    )

    # 创建任务明细
    api_execution_service.add_task_items(db, task.id, [case.id for case in cases])

    db.commit()
    db.refresh(task)

    # 启动 worker 并唤醒以立即处理新任务
    api_task_worker.ensure_processor_running()
    api_task_worker.kick()

    return R.ok(ApiTaskOut.model_validate(task))


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
        db, pid,
        service_id=service_id, status=status, page=page, page_size=page_size,
    )
    return R.ok({
        "total": total, "page": page, "page_size": page_size,
        "items": [ApiTaskOut.model_validate(r) for r in rows],
    })


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


@router.delete("/tasks/{task_id}", response_model=R[dict], summary="删除执行任务")
def delete_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """删除执行任务及其明细（仅终态任务可删）。"""
    pid = _current_project_id(current)
    task = api_execution_service.get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status in ("pending", "running"):
        raise HTTPException(400, "任务执行中，请先取消后再删除")
    api_execution_service.delete_task_items(db, task.id)
    db.delete(task)
    db.commit()
    return {"deleted": task_id}


@router.post("/tasks/{task_id}/cancel", response_model=R[dict], summary="取消任务")
def cancel_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """设置 cancel_requested 标记，由 worker 在下一条 item 执行前检查并终止。"""
    task = api_execution_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    pid = _current_project_id(current)
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")
    if task.status not in ("pending", "running"):
        raise HTTPException(400, "只能取消 pending 或 running 状态的任务")
    task.cancel_requested = True
    db.commit()
    # 唤醒 worker 以立即处理取消
    api_task_worker.kick()
    return R.ok({"status": "cancelling", "task_id": task.id})


@router.post("/tasks/{task_id}/retry-failed", response_model=R[dict], summary="重跑失败用例")
def retry_failed(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """为原任务中所有失败项创建新的重试任务（trigger_type=retry_failed）。

    原任务不受影响；新任务仅包含失败项的 case_id。
    """
    pid = _current_project_id(current)
    task = api_execution_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")

    failed_items = api_execution_service.list_failed_task_items(db, task.id)

    if not failed_items:
        raise HTTPException(400, "没有失败的用例需要重跑")

    # 收集失败用例的 case_id（去重）
    failed_case_ids = list({it.case_id for it in failed_items})

    # 创建新任务
    retry_task_id_str = f"API-{uuid.uuid4().hex[:8].upper()}"
    new_task = api_execution_service.create_execution_task(
        db,
        project_id=pid,
        task_id=retry_task_id_str,
        name=f"{task.name} (失败重试)",
        environment_id=task.environment_id,
        service_id=task.service_id,
        status="pending",
        total=len(failed_case_ids),
        trigger_type="retry_failed",
        creator_id=current.user.id if current.user else 0,
        confirm_prod=task.confirm_prod,
    )

    api_execution_service.add_task_items(db, new_task.id, failed_case_ids)

    db.commit()
    db.refresh(new_task)

    # 唤醒 worker
    api_task_worker.ensure_processor_running()
    api_task_worker.kick()

    return R.ok({
        "new_task_id": new_task.id,
        "new_task_uid": retry_task_id_str,
        "retry_count": len(failed_case_ids),
        "original_task_id": task.id,
    })


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

    return R.ok({
        "total_failed": len(failed_items),
        "categories": categories,
        "analyses": analyses,
    })
