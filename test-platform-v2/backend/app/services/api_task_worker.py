"""持久化 API 任务 Worker — 后台轮询、认领、执行 pending 任务。

设计要点:
- 单后台守护线程，通过 SQLite 事务顺序认领任务（SQLite 不支持 SKIP LOCKED）。
- 每条 item 执行前检查 cancel_requested，已取消则跳过剩余 item。
- Worker 异常不崩溃线程，记录日志后继续轮询。
- 通过 ensure_processor_running() 懒启动，通过 kick() 唤醒。
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

logger = logging.getLogger(__name__)

# ── 进程级状态 ────────────────────────────────────────────
_processor_thread: threading.Thread | None = None
_wake_event = threading.Event()
_shutdown_event = threading.Event()
_processor_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════

def claim_next_task(
    db: Session,
    *,
    worker_id: str,
    project_id: int | None = None,
) -> ApiExecutionTask | None:
    """认领最早的一条 pending 任务。

    SQLite 兼容: 不使用 SKIP LOCKED，依赖单 worker 线程顺序处理。
    调用方可将 db 传入（由 worker 管理的独立 session）。
    """
    q = db.query(ApiExecutionTask).filter(ApiExecutionTask.status == "pending")
    if project_id is not None:
        q = q.filter(ApiExecutionTask.project_id == project_id)
    task = q.order_by(ApiExecutionTask.created_at.asc()).first()
    if not task:
        return None

    task.status = "running"
    task.locked_by = worker_id
    task.locked_at = datetime.now(timezone.utc)
    if task.started_at is None:
        task.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    from app.services.notify_service import queue_notification
    queue_notification(
        task.project_id,
        "task_started",
        {
            "task_type": "API 测试",
            "task_name": task.name or task.task_id,
            "triggered_by": f"user#{task.creator_id}",
            "link": "/apitest",
        },
    )
    return task


def execute_task(task_id: int, project_id: int, worker_id: str) -> None:
    """执行任务的所有 pending item。

    每条 item 执行前检查 task.cancel_requested；
    若取消则跳过剩余 item 并标记任务为 cancelled。
    """
    from app.services.api_execution_service import execute_api_case

    db = SessionLocal()
    try:
        task = db.get(ApiExecutionTask, task_id)
        if not task:
            logger.warning("execute_task: task %s not found", task_id)
            return

        items = db.query(ApiExecutionTaskItem).filter_by(
            task_id=task.id
        ).order_by(ApiExecutionTaskItem.id).all()

        passed = 0
        failed = 0
        skipped = 0

        for item in items:
            # ── 每条 item 执行前检查取消 ──
            db.refresh(task)
            if task.cancel_requested:
                break

            if item.status != "pending":
                # 已被执行或跳过（恢复场景）
                if item.status == "passed":
                    passed += 1
                elif item.status == "failed":
                    failed += 1
                elif item.status == "skipped":
                    skipped += 1
                continue

            # ── 执行 ──
            item.started_at = datetime.now(timezone.utc)
            try:
                result = execute_api_case(
                    db, item.case_id,
                    project_id=project_id,
                    environment_id=task.environment_id,
                    confirm_prod=bool(task.confirm_prod),
                    has_execute_prod=True,  # 已在路由层验证权限
                )
                item.status = "passed" if result.get("all_pass", False) else "failed"
                item.duration_ms = result.get("duration_ms", 0)
                item.request_snapshot = json.dumps(
                    result.get("request_snapshot", {}), ensure_ascii=False,
                )
                item.response_snapshot = _build_response_snapshot(result)
                item.assertion_results = json.dumps(
                    result.get("assertions", []), ensure_ascii=False,
                )
                if result.get("error"):
                    item.error_message = result["error"]
                    item.error_type = "execution_error"

                if item.status == "passed":
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                item.status = "failed"
                item.error_message = str(e)
                item.error_type = type(e).__name__
                failed += 1

            item.finished_at = datetime.now(timezone.utc)
            db.commit()

        # ── 后处理：标记剩余 pending item 为 skipped（若已取消） ──
        db.refresh(task)
        if task.cancel_requested:
            skipped += _skip_pending_items(db, task.id, skipped)
            task.status = "cancelled"
        else:
            if failed == 0 and skipped == 0:
                task.status = "success"
            elif failed > 0:
                task.status = "failed"
            else:
                task.status = "cancelled"

        task.passed = passed
        task.failed = failed
        task.skipped = skipped
        task.finished_at = datetime.now(timezone.utc)
        task.locked_by = ""
        db.commit()

        from app.services.notify_service import queue_notification
        task_name = task.name or task.task_id
        summary = f"通过 {passed} / 失败 {failed} / 跳过 {skipped}"
        queue_notification(
            project_id,
            "task_finished",
            {
                "task_type": "API 测试",
                "task_name": task_name,
                "status": task.status,
                "result_summary": summary,
                "link": "/apitest",
            },
        )
        queue_notification(
            project_id,
            "test_result",
            {
                "task_name": task_name,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": f"{round(passed * 100 / task.total, 1)}%" if task.total else "0%",
                "conclusion": "通过" if failed == 0 and skipped == 0 else task.status,
                "link": "/apitest",
            },
        )

        # M1 入库 hook: 有失败项时沉淀为知识切片
        if failed > 0:
            from app.services.knowledge import ingest_service
            ingest_service.ingest_execution_failure_in_new_session(project_id, task_id)

    except Exception:
        logger.exception("Worker execution failed: task_id=%s", task_id)
        # best-effort: 标记任务为 failed
        try:
            t = db.get(ApiExecutionTask, task_id)
            if t and t.status == "running":
                t.status = "failed"
                t.finished_at = datetime.now(timezone.utc)
                t.locked_by = ""
                db.commit()
                from app.services.notify_service import queue_notification
                queue_notification(
                    project_id,
                    "task_finished",
                    {
                        "task_type": "API 测试",
                        "task_name": t.name or t.task_id,
                        "status": "failed",
                        "result_summary": "执行器异常，详见任务日志",
                        "link": "/apitest",
                    },
                )
        except Exception:
            pass
    finally:
        db.close()


def ensure_processor_running() -> None:
    """启动后台轮询线程（若未启动）。幂等，多次调用安全。"""
    global _processor_thread
    with _processor_lock:
        if _processor_thread is not None and _processor_thread.is_alive():
            return
        _shutdown_event.clear()
        _processor_thread = threading.Thread(
            target=_processor_loop,
            daemon=True,
            name="api-task-worker",
        )
        _processor_thread.start()
        logger.info("API task worker processor started")


def kick() -> None:
    """唤醒 worker 以立即检查新任务。"""
    _wake_event.set()


def shutdown_processor(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程（用于测试和进程退出）。"""
    global _processor_thread
    _shutdown_event.set()
    _wake_event.set()  # 唤醒以检查 shutdown_event
    if _processor_thread is not None:
        _processor_thread.join(timeout=timeout)
        _processor_thread = None
        logger.info("API task worker processor shut down")


# ═══════════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════════

def _processor_loop(poll_interval: float = 2.0) -> None:
    """后台 worker 主循环：轮询 pending 任务 → 认领 → 执行。"""
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    logger.info("Worker loop started: %s", worker_id)

    while not _shutdown_event.is_set():
        db = SessionLocal()
        try:
            task = claim_next_task(db, worker_id=worker_id)
            if task:
                db.close()
                execute_task(task.id, task.project_id, worker_id)
            else:
                db.close()
                # 无 pending 任务 — 等待 kick 或超时
                _wake_event.wait(timeout=poll_interval)
                _wake_event.clear()
        except Exception:
            logger.exception("Worker loop error")
            try:
                db.close()
            except Exception:
                pass
            _wake_event.wait(timeout=poll_interval)
            _wake_event.clear()

    logger.info("Worker loop stopped: %s", worker_id)


def _skip_pending_items(db: Session, task_id: int, current_skip_count: int) -> int:
    """将任务的所有 pending item 标记为 skipped，返回新增 skip 数。"""
    pending_items = db.query(ApiExecutionTaskItem).filter_by(
        task_id=task_id, status="pending",
    ).all()
    for it in pending_items:
        it.status = "skipped"
        it.error_message = "任务已取消"
        it.finished_at = datetime.now(timezone.utc)
    if pending_items:
        db.commit()
    return len(pending_items)


def _build_response_snapshot(result: dict) -> str:
    """构建结构化响应快照 JSON 字符串（与 apitest.py 中一致）。"""
    snapshot = result.get("response_snapshot", {})
    if not snapshot:
        # 兼容没有 response_snapshot 的旧版结果
        raw_body = result.get("raw_body") or ""
        body_size = len(raw_body) if raw_body else 0
        preview_max = 4096
        body_preview = raw_body[:preview_max] if len(raw_body) > preview_max else raw_body
        snapshot = {
            "status_code": result.get("status_code"),
            "headers": result.get("response_headers", {}),
            "body_preview": body_preview,
            "body_size_bytes": body_size,
            "truncated": len(raw_body) > preview_max,
            "content_type": result.get("response_headers", {}).get("content-type", ""),
        }
    # Always ensure body_preview and truncated are populated
    if "body_preview" not in snapshot:
        snapshot["body_preview"] = ""
    if "truncated" not in snapshot:
        snapshot["truncated"] = False
    return json.dumps(snapshot, ensure_ascii=False, default=str)
