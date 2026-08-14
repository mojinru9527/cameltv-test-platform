"""持久化 API 任务 Worker — 后台轮询、认领、执行 pending 任务。

设计要点:
- 单后台守护线程，通过事务原子认领任务。
- Batch 174（FIX-173-P0-01/02）：
  ① PostgreSQL 下使用 `with_for_update(skip_locked=True)` 原子认领，
     消除双 Worker/多副本下 SELECT→UPDATE 的 TOCTOU 重复执行；
  ② 认领前回收失联的 running 任务（locked_at 心跳超时置 failed），
     消除「任务永久卡 running」的僵尸任务；
  ③ task_worker.py 已移除 API 分支，本 worker 是 API 批量任务的唯一执行者。
- 每条 item 执行前检查 cancel_requested，已取消则跳过剩余 item。
- Worker 异常不崩溃线程，记录日志后继续轮询。
- 通过 ensure_processor_running() 懒启动，通过 kick() 唤醒。
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

logger = logging.getLogger(__name__)

# ── 进程级状态 ────────────────────────────────────────────
_processor_thread: threading.Thread | None = None
_wake_event = threading.Event()
_shutdown_event = threading.Event()
_processor_lock = threading.Lock()

# Batch 174：认领后失联超时即视为僵尸（默认 30 分钟，可被测试覆盖）
STALE_LOCK_SECONDS = 30 * 60


# ═══════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════

def reap_stale_api_tasks(db: Session) -> int:
    """回收失联的 API 批量任务（FIX-173-P0-01）。

    运行中任务 locked_at 超过 STALE_LOCK_SECONDS 未更新即视为执行器失联，
    置 failed 并释放锁，允许后续重试/重新创建。仿 core/scheduler.reap_stale_schedule_runs。
    """
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=STALE_LOCK_SECONDS)
    rows = db.query(ApiExecutionTask).filter(
        ApiExecutionTask.status == "running",
        ApiExecutionTask.locked_at.isnot(None),
        ApiExecutionTask.locked_at < stale_before,
    ).all()
    reaped = 0
    for task in rows:
        task.status = "failed"
        task.finished_at = datetime.now(timezone.utc)
        task.locked_by = ""
        task.error_message = (
            f"stale: 执行器失联超过 {STALE_LOCK_SECONDS // 60} 分钟，已回收（Batch 174）"
        )
        reaped += 1
    if reaped:
        db.commit()
        logger.warning("[api-task-worker] Reaped %s stale API task(s)", reaped)
    else:
        db.rollback()
    return reaped


def claim_next_task(
    db: Session,
    *,
    worker_id: str,
    project_id: int | None = None,
) -> ApiExecutionTask | None:
    """原子认领最早的一条 pending 任务。

    Batch 174（FIX-173-P0-02）：PostgreSQL 下 `with_for_update(skip_locked=True)`
    保证并发 Worker/多副本只有一个能认领到同一条任务（TOCTOU 修复）；
    SQLite 不支持 SKIP LOCKED，`with_for_update()` 在 SQLite 下退化为行锁语义，
    配合本模块单守护线程（_processor_loop）串行轮询，同样安全。
    """
    # 先回收失联任务，避免僵尸 running 阻塞后续执行
    reap_stale_api_tasks(db)

    q = db.query(ApiExecutionTask).filter(ApiExecutionTask.status == "pending")
    if project_id is not None:
        q = q.filter(ApiExecutionTask.project_id == project_id)
    q = q.order_by(ApiExecutionTask.created_at.asc())
    try:
        task = q.with_for_update(skip_locked=True).first()
    except Exception:
        # SQLite 等不支持 skip_locked 的方言回退为普通行锁
        logger.debug("skip_locked unsupported, fallback to plain select")
        db.rollback()
        task = (
            db.query(ApiExecutionTask)
            .filter(ApiExecutionTask.status == "pending")
            .order_by(ApiExecutionTask.created_at.asc())
            .first()
        )
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

                # Batch 111（C110-3/C103-7）：回填用例详情「请求结果」，
                # 保证批量执行后用例详情三栏（请求参数/断言/请求结果）闭环。
                from app.models.test_case import TestCase as TestCaseModel
                case_row = db.get(TestCaseModel, item.case_id)
                if case_row:
                    if result.get("error"):
                        case_row.last_response_json = json.dumps(
                            {"error": result["error"]}, ensure_ascii=False,
                        )
                    else:
                        case_row.last_response_json = _build_response_snapshot(result)
                    case_row.last_run_status = item.status
                    db.add(case_row)
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
            logger.warning("标记任务失败状态失败（静默降级为仅 DB 记录）")
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
    with _processor_lock:
        thread = _processor_thread
        if thread is None:
            return
        _shutdown_event.set()
        _wake_event.set()  # 唤醒以检查 shutdown_event

    thread.join(timeout=timeout)
    if thread.is_alive():
        logger.warning("API task worker did not stop within %.1fs", timeout)
        return

    with _processor_lock:
        if _processor_thread is thread:
            _processor_thread = None
            logger.info("API task worker processor shut down")


# ═══════════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════════

def _processor_loop(poll_interval: float = 2.0) -> None:
    """后台 worker 主循环：轮询 pending 任务 → 认领 → 执行。"""
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    logger.info("Worker loop started: %s", worker_id)

    idle_cycles = 0
    while not _shutdown_event.is_set():
        db = SessionLocal()
        try:
            task = claim_next_task(db, worker_id=worker_id)
            if task:
                idle_cycles = 0
                db.close()
                execute_task(task.id, task.project_id, worker_id)
            else:
                db.close()
                idle_cycles += 1
                # 兜底：无任务时周期性回收僵尸任务（claim 内部已回收，
                # 这里额外覆盖「worker 自身崩溃后无人认领」的极端场景）
                if idle_cycles % 30 == 0:
                    try:
                        reap_db = SessionLocal()
                        try:
                            reaped = reap_stale_api_tasks(reap_db)
                            if reaped:
                                logger.warning("[api-task-worker] Idle reap: %s stale task(s)", reaped)
                        finally:
                            reap_db.close()
                    except Exception:
                        logger.exception("Idle stale reap failed")
                # 无 pending 任务 — 等待 kick 或超时
                _wake_event.wait(timeout=poll_interval)
                _wake_event.clear()
        except Exception:
            logger.exception("Worker loop error")
            try:
                db.close()
            except Exception:
                logger.warning("DB session 关闭失败")
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
