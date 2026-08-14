"""DSH 任务执行服务 — Batch 172。

提交/查询/取消 + 后台 worker（DB 认领，多 worker 可消费，模式对齐 ai_tasks.py）。
worker 执行时调用 dsh_runner.run_dsh_task，状态与输出落库。
"""
from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update

from app.core.db import SessionLocal
from app.models.dsh_task import DshTask

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_worker_thread: threading.Thread | None = None
_wake_event = threading.Event()
_shutdown_event = threading.Event()
_worker_lock = threading.Lock()

_STALE_CLAIM_SECONDS = 300


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def submit_task(
    db,
    *,
    project_id: int,
    task: str,
    params: dict | None = None,
    operator_id: int = 0,
) -> DshTask:
    """插入 pending 任务并唤醒 worker（多 worker 部署下任何进程均可认领）。"""
    row = DshTask(
        project_id=project_id,
        task=task,
        status="pending",
        params_json=json.dumps(params or {}, ensure_ascii=False),
        operator_id=operator_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ensure_worker_running()
    _wake_event.set()
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
    """认领最早 pending 任务（stale 锁可重认领），避免多 worker 重复执行。"""
    now = now or _now()
    stale = now - timedelta(seconds=_STALE_CLAIM_SECONDS)
    row = db.scalar(
        select(DshTask)
        .where(DshTask.status == "pending")
        .where(or_(DshTask.started_at.is_(None), DshTask.started_at < stale))
        .order_by(DshTask.created_at)
        .limit(1)
    )
    if row is None:
        return None
    result = db.execute(
        update(DshTask)
        .where(DshTask.id == row.id, DshTask.status == "pending")
        .values(status="running", started_at=now)
    )
    db.commit()
    if result.rowcount == 0:
        return None
    db.refresh(row)
    return row


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


def _worker_loop() -> None:
    while not _shutdown_event.is_set():
        _wake_event.wait(timeout=1.0)
        _wake_event.clear()
        if _shutdown_event.is_set():
            break
        try:
            db = SessionLocal()
            try:
                task = claim_next_task(db)
                if task is not None:
                    _executor.submit(_process_claimed, task.id)
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001 - 轮询失败不退出
            logger.warning("DSH task worker poll error: %s", exc)


def ensure_worker_running() -> None:
    """启动后台轮询线程（幂等）。"""
    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return
        _shutdown_event.clear()
        _worker_thread = threading.Thread(
            target=_worker_loop,
            daemon=True,
            name="dsh-task-worker",
        )
        _worker_thread.start()
        logger.info("DSH task worker started")


def shutdown_worker(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程（测试/退出用）。"""
    global _worker_thread
    with _worker_lock:
        thread = _worker_thread
        if thread is None:
            return
        _shutdown_event.set()
        _wake_event.set()
    thread.join(timeout=timeout)
    with _worker_lock:
        _worker_thread = None
