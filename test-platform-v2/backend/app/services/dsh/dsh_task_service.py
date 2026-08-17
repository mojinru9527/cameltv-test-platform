"""DSH 任务执行服务 — Batch 172。

提交/查询/取消 + 后台 worker（DB 认领，多 worker 可消费，模式对齐 ai_tasks.py）。
worker 执行时调用 dsh_runner.run_dsh_task，状态与输出落库。

Batch 181（FIX-173-P2-06）：认领/回收/循环骨架收敛到 app.core.task_queue 统一原语；
模型补 locked_at/locked_by 列（20260816_b181_task_queue_locks），
started_at 不再兼作锁字段。
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.task_queue import (
    QueueSpec,
    QueueWorkerLoop,
    atomic_claim,
    utcnow,
)
from app.models.dsh_task import DshTask

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

_STALE_CLAIM_SECONDS = 300

_DSH_QUEUE = QueueSpec(
    model=DshTask,
    id_col="id",
    status_col="status",
    pending="pending",
    running="running",
    failed="failed",
    lock_by_col="locked_by",
    lock_at_col="locked_at",
    order_col="created_at",
    order_asc=True,
)

_loop = QueueWorkerLoop(name="dsh-task-worker", poll_interval=1.0, on_tick=lambda: _poll_once())


def _now() -> datetime:
    return utcnow()


def submit_task(
    db,
    *,
    project_id: int,
    task: str,
    params: dict | None = None,
    mode: str = "single",
    operator_id: int = 0,
) -> DshTask:
    """插入 pending 任务并唤醒 worker（多 worker 部署下任何进程均可认领）。"""
    row = DshTask(
        project_id=project_id,
        task=task,
        status="pending",
        params_json=json.dumps(params or {}, ensure_ascii=False),
        operator_id=operator_id,
        mode=mode,
        team_json="{}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ensure_worker_running()
    _loop.kick()
    return row


def list_tasks(
    db,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DshTask], int]:
    from sqlalchemy import func

    stmt = select(DshTask).where(DshTask.project_id == project_id)
    cnt = select(func.count(DshTask.id)).where(DshTask.project_id == project_id)
    if status:
        stmt = stmt.where(DshTask.status == status)
        cnt = cnt.where(DshTask.status == status)
    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(DshTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_task(db, task_id: int, project_id: int) -> DshTask | None:
    row = db.get(DshTask, task_id)
    if not row or row.project_id != project_id:
        return None
    return row


def cancel_task(db, task_id: int, project_id: int) -> DshTask | None:
    """仅 pending 可取消。返回更新后的任务或 None（不存在/不可取消）。"""
    row = db.get(DshTask, task_id)
    if not row or row.project_id != project_id:
        return None
    if row.status != "pending":
        return None
    row.status = "cancelled"
    row.finished_at = _now()
    db.commit()
    db.refresh(row)
    return row


def claim_next_task(db, now: datetime | None = None) -> DshTask | None:
    """认领最早 pending 任务（stale 锁可重认领），Batch 181 起走统一原语。"""
    return atomic_claim(db, _DSH_QUEUE, worker_id="dsh-worker", stale_seconds=_STALE_CLAIM_SECONDS)


def execute_task(db, task: DshTask, runner=None) -> None:
    """执行已认领任务并写回结果/错误。runner 可注入用于测试。"""
    from app.services.dsh.dsh_runner import run_dsh_task

    runner = runner or run_dsh_task
    try:
        params = {}
        try:
            params = json.loads(task.params_json or "{}")
        except json.JSONDecodeError:
            params = {}
        result = runner(task.task, workspace=params.get("workspace") or None)
        task.status = "success" if result.exit_code == 0 else "failed"
        task.output_text = (result.final_response or "")[:20000]
        task.error = (result.error or "")[:2000] if result.exit_code != 0 else ""
        task.session_dir = result.session_dir
        task.finished_at = _now()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 任务失败写回
        task.status = "failed"
        task.error = str(exc)[:2000]
        task.finished_at = _now()
        db.commit()


def _process_claimed(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(DshTask, task_id)
        if task is None or task.status != "running":
            return
        execute_task(db, task)
    finally:
        db.close()


def _poll_once() -> None:
    """单次轮询：原子认领一条任务并提交到执行池。"""
    db = SessionLocal()
    try:
        task = claim_next_task(db)
        if task is not None:
            _executor.submit(_process_claimed, task.id)
    except Exception as exc:  # noqa: BLE001 - 轮询失败不退出
        logger.warning("DSH task worker poll error: %s", exc)
    finally:
        db.close()


def ensure_worker_running() -> None:
    """启动后台轮询线程（幂等）。"""
    _loop.start()


def shutdown_worker(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程（测试/退出用）。"""
    _loop.shutdown(timeout=timeout)
