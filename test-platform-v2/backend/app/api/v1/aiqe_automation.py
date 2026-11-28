"""AUD-014/015/017/018/019/020/013：v1.5 §06 目标契约的 REST 面。

所有路由都复用已交付的 service（不新增业务逻辑），并遵守统一的：
project scope（`current.project_id`）、RBAC（`menu:aiqe_runs` / `defect:update`）、
错误映射（400/403/404/422）、以及"前端不得自报事实"的约束。
"""
from __future__ import annotations


from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services import (
    regression_terminal,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Capabilities"])

_console = require_permission("menu:aiqe_runs")
_edit = require_permission("defect:update")


def _bad(message: str, status: int = 400) -> APIException:
    return APIException(code=status, msg=message, http_status=status)


# ── Agent task plan (AUD-013 / V16-013 / FIX-005) ─────────────────
class AgentTaskIn(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)
    include: list[str] | None = None
    run_id: str | None = None
    input_refs: list[str] | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)
    submit: bool = False
    # FIX-005：PR/Git 变更范围（可选）。两个 SHA 必须同时提供，服务端要求完整
    # 40 位小写 hex；A5 只通过受控工具 read_git_diff 读取服务端 diff。
    base_sha: str | None = Field(default=None, max_length=40)
    head_sha: str | None = Field(default=None, max_length=40)
    repo: str | None = Field(default=None, max_length=200)


class ApprovalIn(BaseModel):
    reason: str = Field(default="", max_length=500)
    expected_plan_hash: str | None = None


def _agent_task_out(row) -> dict:
    scope = {}
    try:
        from app.aiqe.services.agent_task_service import task_change_scope

        scope = task_change_scope(row)
    except Exception:  # 展示字段失败不得影响主流程
        scope = {}
    return {
        "task_id": row.id,
        "status": row.status,
        "goal": row.goal,
        "plan_id": (row.plan_json or {}).get("plan_id"),
        "plan_hash": row.plan_hash,
        "approval_required": row.status in {"DRAFT", "PENDING_APPROVAL"},
        "approved_by": row.approved_by,
        "approved_at": row.approved_at,
        "error_code": row.error_code,
        "result_refs": list(row.result_refs_json or []),
        "change_scope": scope,
        "tasks": [
            {
                "task_id": task.get("task_id"),
                "agent_key": task.get("agent_key"),
                "depends_on": task.get("depends_on") or [],
            }
            for task in (row.plan_json or {}).get("tasks") or []
        ],
    }


@router.post("/agent-tasks", response_model=R[dict], summary="A0 任务计划 Draft（不执行 Agent）")
def create_agent_task_api(
    body: AgentTaskIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import (
        AgentTaskError,
        create_task,
        submit_task,
    )

    try:
        row = create_task(
            db,
            project_id=int(current.project_id or 0),
            goal=body.goal,
            include=tuple(body.include) if body.include else None,
            input_refs=list(body.input_refs or []),
            requested_by=current.user.id,
            idempotency_key=body.idempotency_key,
            run_id=body.run_id,
            base_sha=body.base_sha,
            head_sha=body.head_sha,
            repo=body.repo,
        )
        if body.submit:
            row = submit_task(db, row.id, project_id=int(current.project_id or 0))
    except AgentTaskError as exc:
        raise _bad(f"{exc.code}: {exc}", 400) from None
    db.commit()
    return R.ok(_agent_task_out(row))


@router.get("/agent-tasks/{task_id}", response_model=R[dict], summary="AgentTask 详情")
def get_agent_task_api(
    task_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import AgentTaskError, get_task

    try:
        row = get_task(db, task_id, project_id=int(current.project_id or 0))
    except AgentTaskError:
        raise _bad("AgentTask 不存在", 404) from None
    return R.ok(_agent_task_out(row))


@router.post(
    "/agent-tasks/{task_id}/submit", response_model=R[dict], summary="提交人工审批"
)
def submit_agent_task_api(
    task_id: str,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import (
        AgentTaskError,
        get_task,
        submit_task,
    )

    try:
        get_task(db, task_id, project_id=int(current.project_id or 0))
        row = submit_task(db, task_id, project_id=int(current.project_id or 0))
    except AgentTaskError as exc:
        raise _bad(str(exc), 404 if "不存在" in str(exc) else 400) from None
    db.commit()
    return R.ok(_agent_task_out(row))


@router.post(
    "/agent-tasks/{task_id}/approve", response_model=R[dict], summary="人工审批（记录审批人）"
)
def approve_agent_task_api(
    task_id: str,
    body: ApprovalIn | None = None,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import AgentTaskError, approve_task

    try:
        row = approve_task(
            db,
            task_id,
            project_id=int(current.project_id or 0),
            approved_by=current.user.id,
            reason=(body.reason if body else ""),
            expected_plan_hash=(body.expected_plan_hash if body else None),
        )
    except AgentTaskError as exc:
        status = 404 if exc.code == "TASK_NOT_FOUND" else 400
        raise _bad(str(exc), status) from None
    db.commit()
    return R.ok(_agent_task_out(row))


@router.post(
    "/agent-tasks/{task_id}/run",
    response_model=R[dict],
    status_code=202,
    summary="审批后入队执行（Outbox + ExecutionJob，不在请求线程执行）",
)
def run_agent_task_api(
    task_id: str,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import (
        AgentTaskError,
        enqueue_task_job,
        get_task,
    )

    try:
        row = get_task(db, task_id, project_id=int(current.project_id or 0))
        if row.status != "APPROVED":
            raise AgentTaskError(
                "APPROVAL_REQUIRED", f"Task 未审批或已执行（当前 {row.status}）"
            )
        job = enqueue_task_job(db, row)
    except AgentTaskError as exc:
        raise _bad(str(exc), 409 if exc.code == "APPROVAL_REQUIRED" else 400) from None
    db.commit()
    return R.ok({"task_id": row.id, "job_id": job.id, "status": row.status})


@router.post(
    "/agent-tasks/{task_id}/cancel", response_model=R[dict], summary="取消 AgentTask"
)
def cancel_agent_task_api(
    task_id: str,
    reason: str = "",
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    from app.aiqe.services.agent_task_service import AgentTaskError, cancel_task

    try:
        row = cancel_task(
            db, task_id, project_id=int(current.project_id or 0), reason=reason
        )
    except AgentTaskError as exc:
        raise _bad(str(exc), 404 if "不存在" in str(exc) else 400) from None
    db.commit()
    return R.ok(_agent_task_out(row))


@router.post(
    "/regressions/{regression_id}/sync", response_model=R[dict], summary="回归终态同步（幂等）"
)
def sync_regression_api(
    regression_id: int,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
    _edit: CurrentUser = Depends(_edit),
):
    from app.aiqe.services.regression_service import RegressionNotFound, get_regression

    try:
        regression = get_regression(db, regression_id, current.project_id or 0)
    except RegressionNotFound:
        raise _bad(f"回归请求不存在: {regression_id}", 404) from None
    if not regression.verification_run_id:
        return R.ok({"regression_id": regression.id, "skipped": True, "reason": "NO_RUN"})
    result = regression_terminal.handle_run_terminal(
        db, run_id=regression.verification_run_id
    )
    db.commit()
    return R.ok(result.payload())


__all__ = ["router"]
