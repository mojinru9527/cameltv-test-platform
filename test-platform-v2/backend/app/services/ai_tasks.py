"""C102-1/C117-2 — AI 生成/提取异步任务（DB 队列，多 worker 可消费）。

请求先返回 task_id；后台 worker 从 DB 原子认领 pending 任务执行（任何进程的
worker 都可认领，避免单进程注册表在多 worker 部署下丢任务）。前端轮询
GET /requirements/ai-task/{task_id}。
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update

from app.core.db import SessionLocal
from app.models.ai_task import AiTask

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_worker_thread: threading.Thread | None = None
_wake_event = threading.Event()
_shutdown_event = threading.Event()
_worker_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_dict(row: AiTask) -> dict:
    return {
        "id": row.id,
        "type": row.task_type,
        "project_id": row.project_id,
        "document_id": row.document_id,
        "status": row.status,
        "progress": row.progress,
        "result": json.loads(row.result_json) if row.result_json and row.result_json != "null" else None,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def submit_ai_task(*, document_id: int, task_type: str, project_id: int) -> dict:
    """插入 pending 任务并唤醒 worker（多 worker 部署下任何进程均可认领）。"""
    task_id = f"ai-{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        db.add(AiTask(
            id=task_id,
            task_type=task_type,
            project_id=project_id,
            document_id=document_id,
            status="pending",
            progress=0,
            result_json="null",
            error="",
        ))
        db.commit()
    finally:
        db.close()
    ensure_worker_running()
    _wake_event.set()
    return get_ai_task(task_id) or {"id": task_id, "status": "pending"}


def get_ai_task(task_id: str) -> dict | None:
    db = SessionLocal()
    try:
        row = db.get(AiTask, task_id)
        return _to_dict(row) if row else None
    finally:
        db.close()


def claim_next_task(db, now: datetime | None = None) -> AiTask | None:
    """认领最早的 pending 任务（stale 锁可重认领）。

    先取最早 pending，再以 status='pending' 条件 UPDATE——多 worker 下第二个
    UPDATE 命中 0 行即返回 None，避免重复执行。
    """
    now = now or _now()
    stale = now - timedelta(minutes=5)
    row = db.scalar(
        select(AiTask)
        .where(AiTask.status == "pending")
        .where(or_(AiTask.locked_at.is_(None), AiTask.locked_at < stale))
        .order_by(AiTask.created_at)
        .limit(1)
    )
    if row is None:
        return None
    result = db.execute(
        update(AiTask)
        .where(AiTask.id == row.id, AiTask.status == "pending")
        .values(status="running", progress=5, locked_at=now, started_at=now)
    )
    db.commit()
    if result.rowcount == 0:
        return None
    db.refresh(row)
    return row


def _run_extract(db, document_id: int) -> dict:
    from app.services.requirement_service import get_requirement

    doc = get_requirement(db, document_id, project_id=0) or {}
    content = doc.get("content") or doc.get("requirement_text") or ""
    import asyncio
    from app.services.ai_service import extract_features as _ai_extract

    return asyncio.run(_ai_extract(
        content,
        file_type=doc.get("file_type", ""),
        source_ref=str(doc.get("source_ref") or ""),
    ))


def _run_generate(db, document_id: int) -> dict:
    from app.services.requirement_service import get_requirement

    doc = get_requirement(db, document_id, project_id=0) or {}
    content = doc.get("content") or doc.get("requirement_text") or ""
    from app.services.ai_service import generate_test_cases as _ai_gen
    from app.services.coverage_report import build_coverage_report, parse_extraction

    import asyncio

    result = asyncio.run(_ai_gen(
        content,
        file_type=doc.get("file_type", ""),
        source_ref=str(doc.get("source_ref") or ""),
    ))
    extraction = parse_extraction(str(doc.get("extraction_raw") or ""))
    result["coverage_report"] = build_coverage_report(extraction, result)
    return result


def _dispatch(task_type: str, document_id: int, db) -> dict:
    if task_type == "extract":
        return _run_extract(db, document_id)
    if task_type == "generate":
        return _run_generate(db, document_id)
    raise ValueError(f"未知任务类型: {task_type}")


def execute_task(db, task: AiTask, dispatch=None) -> None:
    """执行已认领任务并写回结果/错误。dispatch 可注入用于测试。"""
    dispatch = dispatch or _dispatch
    try:
        result = dispatch(task.task_type, task.document_id, db)
        task.status = "done"
        task.progress = 100
        task.result_json = json.dumps(result, ensure_ascii=False, default=str)
        task.locked_at = None
        task.finished_at = _now()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 任务失败写回
        task.status = "failed"
        task.error = str(exc)[:500]
        task.locked_at = None
        task.finished_at = _now()
        db.commit()


def _process_claimed(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(AiTask, task_id)
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
            logger.warning("AI task worker poll error: %s", exc)


def ensure_worker_running() -> None:
    """启动后台轮询线程（幂等）。每个进程一个 worker，均可认领 DB 中的任务。"""
    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return
        _shutdown_event.clear()
        _worker_thread = threading.Thread(
            target=_worker_loop,
            daemon=True,
            name="ai-task-worker",
        )
        _worker_thread.start()
        logger.info("AI task worker started")


def shutdown_worker(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程。"""
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
