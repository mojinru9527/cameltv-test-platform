"""UI runner 队列 — 进程本地线程 + 信号量并发控制。

使用 ThreadPoolExecutor 实现并发限制，提供 enqueue_run / running_count /
ensure_processor_running 三个模块级 API 作为适配器边界，方便未来
迁移到 RQ/Celery/Arq 等生产级任务队列。
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from app.services.playwright_executor import MAX_CONCURRENT

logger = logging.getLogger("ui_runner_queue")

_executor: ThreadPoolExecutor | None = None
_running: int = 0
_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """懒初始化线程池（max_workers = MAX_CONCURRENT）。"""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT,
            thread_name_prefix="ui-runner-",
        )
        logger.info("UI runner thread pool started (max_workers=%d)", MAX_CONCURRENT)
    return _executor


def ensure_processor_running() -> None:
    """确保处理器已就绪（懒初始化线程池）。"""
    _get_executor()


def enqueue_run(run_id: int, job_id: int, project_id: int) -> None:
    """将一次 UI 测试运行加入队列。

    提交到线程池执行，最多 MAX_CONCURRENT 个任务并行，
    超出部分在线程池内部排队。
    """
    global _running
    with _lock:
        _running += 1
    _get_executor().submit(_execute_run, run_id, job_id, project_id)
    logger.info("Enqueued UI run #%s (job #%s, project %s)", run_id, job_id, project_id)


def running_count() -> int:
    """返回当前正在执行的 runner 数量。"""
    with _lock:
        return _running


def queue_size() -> int:
    """返回线程池中等待执行的任务数（近似值）。"""
    ex = _executor
    if ex is None:
        return 0
    return getattr(ex, "_work_queue", None) and ex._work_queue.qsize() or 0


def shutdown_processor(timeout: float = 30.0) -> None:
    """优雅关闭线程池（等待当前任务完成）。"""
    global _executor
    if _executor is not None:
        logger.info("Shutting down UI runner thread pool (timeout=%.0fs)", timeout)
        _executor.shutdown(wait=True, cancel_futures=False)
        _executor = None
        logger.info("UI runner thread pool stopped")


# ── 内部实现 ──

def _execute_run(run_id: int, job_id: int, project_id: int) -> None:
    """在独立 DB session 中执行一次 Playwright 测试。"""
    global _running
    from datetime import datetime, timezone
    from app.core.db import SessionLocal
    from app.services.playwright_executor import run_playwright_test
    from app.models.ui_test import UiTestRun, UiTestJob

    db = SessionLocal()
    try:
        logger.info("Starting UI run #%s (job #%s)", run_id, job_id)
        run_playwright_test(db, run_id, job_id, project_id)
        logger.info("Completed UI run #%s", run_id)
    except Exception:
        logger.exception("UI runner crashed for run #%s", run_id)
        try:
            run = db.get(UiTestRun, run_id)
            if run and run.status == "running":
                run.status = "fail"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = "执行器内部异常"
                job = db.get(UiTestJob, job_id)
                if job:
                    job.status = "fail"
                db.commit()
        except Exception:
            logger.exception("Failed to update run/job after crash: run_id=%s", run_id)
    finally:
        db.close()
        with _lock:
            _running = max(0, _running - 1)
