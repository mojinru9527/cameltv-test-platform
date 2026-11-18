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


# ── Agent task plan (AUD-013) ───────────────────────────
class AgentTaskIn(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)
    include: list[str] | None = None


@router.post("/agent-tasks", response_model=R[dict], summary="A0 任务计划 Draft")
def create_agent_task_api(
    body: AgentTaskIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from app.aiqe.agents.orchestrator import build_plan
    from app.aiqe.agents.protocol import AgentContext
    from app.aiqe.agents.registry import get_agent

    try:
        plan = build_plan(body.goal, include=tuple(body.include) if body.include else None)
    except Exception as exc:  # PlanError
        raise _bad(str(exc)) from None
    agent = get_agent("A0")
    result = agent.execute(AgentContext(project_id=current.project_id or 0), body.goal)
    return R.ok(
        {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "agent_key": task.agent_key,
                    "depends_on": list(task.depends_on),
                    "allowed_tools": list(task.allowed_tools),
                }
                for task in plan.order()
            ],
            "a0_status": result.status,
            "a0_output": result.output,
        }
    )


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
