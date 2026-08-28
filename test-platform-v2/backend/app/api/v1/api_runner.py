"""内网执行器 API — 平台派发 / runner 认领执行 / 回传结果。

Batch 206 / C-内网执行器：/api/v1/apitest/runner/*
- POST /tasks        平台为 internal+runner 环境创建派发任务
- POST /claim        runner 认领一条 pending 任务
- POST /report       runner 回传执行结果
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import runner_execution_service as svc

router = APIRouter(prefix="/apitest/runner", tags=["接口测试-内网执行器"])


class RunnerTaskCreateRequest(BaseModel):
    environment_id: int
    task_id: str = Field(default="", max_length=64)
    request: dict
    assertions: list[dict] = Field(default_factory=list)
    runner_key: str = Field(default="", max_length=64)


class RunnerClaimRequest(BaseModel):
    runner_key: str = Field(default="", max_length=64)


class RunnerReportRequest(BaseModel):
    task_id: int
    status: str = Field(..., pattern=r"^(done|failed|error)$")
    result: dict = Field(default_factory=dict)
    error_message: str = Field(default="", max_length=4000)


def _pid(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


@router.post("/tasks", response_model=R[dict], summary="创建内网执行器任务")
def create_runner_task(
    body: RunnerTaskCreateRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    pid = _pid(current)
    task = svc.create_runner_task(
        db, pid, body.environment_id, body.task_id, body.request, body.assertions, body.runner_key
    )
    db.commit()
    return R.ok({"task_id": task.id, "status": task.status, "execution_id": task.task_id})


@router.post("/claim", response_model=R[dict], summary="runner 认领任务")
def claim_runner_task(
    body: RunnerClaimRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    task = svc.claim_runner_task(db, body.runner_key)
    if not task:
        return R.ok({"claimed": False, "message": "无待认领任务"})
    return R.ok({
        "claimed": True,
        "task_id": task.id,
        "execution_id": task.task_id,
        "environment_id": task.environment_id,
        "project_id": task.project_id,
        "request": json.loads(task.request),
        "assertions": json.loads(task.assertions),
    })


@router.post("/report", response_model=R[dict], summary="runner 回传结果")
def report_runner_task(
    body: RunnerReportRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    task = svc.report_runner_task(db, body.task_id, status=body.status, result=body.result, error_message=body.error_message)
    if not task:
        raise HTTPException(404, "任务不存在或状态不合法")
    return R.ok({"task_id": task.id, "status": task.status})


@router.get("/tasks", response_model=R[dict], summary="平台查看内网执行器任务")
def list_runner_tasks(
    status: str | None = None,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    tasks = svc.list_runner_tasks(db, _pid(current), status)
    return R.ok({"total": len(tasks), "items": [
        {"id": t.id, "execution_id": t.task_id, "status": t.status, "runner_key": t.runner_key,
         "environment_id": t.environment_id, "finished_at": t.finished_at.isoformat() if t.finished_at else None}
        for t in tasks
    ]})
