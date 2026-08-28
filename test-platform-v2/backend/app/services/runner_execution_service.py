"""内网执行器任务服务 — 平台派发 / runner 认领执行 / 回传结果。

Batch 206 / C-内网执行器：internal 环境 + execution_mode=runner 时，
平台不直连内网，创建 RunnerExecutionTask，由内网执行器（runner_key）认领执行。
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.runner_execution import RunnerExecutionTask


def create_runner_task(
    db: Session,
    project_id: int,
    environment_id: int,
    task_id: str,
    request: dict,
    assertions: list[dict],
    runner_key: str = "",
) -> RunnerExecutionTask:
    """平台侧：为 internal+runner 环境创建派发任务。"""
    task = RunnerExecutionTask(
        project_id=project_id,
        environment_id=environment_id,
        task_id=task_id,
        runner_key=runner_key,
        request=json.dumps(request, ensure_ascii=False),
        assertions=json.dumps(assertions, ensure_ascii=False),
        status="pending",
    )
    db.add(task)
    db.flush()
    return task


def claim_runner_task(db: Session, runner_key: str) -> RunnerExecutionTask | None:
    """runner 侧：认领一条 pending 任务（匹配 runner_key，空 runner_key 可由任意 runner 认领）。

    原子认领：SELECT ... FOR UPDATE SKIP LOCKED 避免多 runner 抢同一条。
    """
    task = (
        db.query(RunnerExecutionTask)
        .filter(
            RunnerExecutionTask.status == "pending",
            (RunnerExecutionTask.runner_key == "") | (RunnerExecutionTask.runner_key == runner_key),
        )
        .with_for_update(skip_locked=True)
        .first()
    )
    if task:
        task.status = "claimed"
        task.locked_by = runner_key
        task.locked_at = datetime.now()
        task.claimed_at = datetime.now()
        db.commit()
        db.refresh(task)
    return task


def report_runner_task(
    db: Session,
    task_id: int,
    *,
    status: str,
    result: dict,
    error_message: str = "",
) -> RunnerExecutionTask | None:
    """runner 侧：回传执行结果（done/failed）。"""
    task = db.get(RunnerExecutionTask, task_id)
    if not task or task.status not in ("claimed", "pending", "done", "failed"):
        return None
    task.status = "done" if status not in ("failed", "error") else "failed"
    task.result = json.dumps(result, ensure_ascii=False)
    task.error_message = error_message
    task.finished_at = datetime.now()
    db.commit()
    db.refresh(task)
    return task


def get_runner_task(db: Session, task_id: int) -> RunnerExecutionTask | None:
    return db.get(RunnerExecutionTask, task_id)


def list_runner_tasks(db: Session, project_id: int, status: str | None = None) -> list[RunnerExecutionTask]:
    q = db.query(RunnerExecutionTask).filter(RunnerExecutionTask.project_id == project_id)
    if status:
        q = q.filter(RunnerExecutionTask.status == status)
    return q.order_by(RunnerExecutionTask.id.desc()).limit(100).all()
