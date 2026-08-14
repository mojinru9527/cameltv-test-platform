"""独立任务 Worker — 轮询 pending 任务并执行，替代 BackgroundTasks。

特性：
- 轮询间隔可配（默认 5 秒）
- 并发上限控制
- 服务重启后 pending 任务自动恢复
- 同时处理 UI 测试运行和蓝湖证据包任务

Batch 174（FIX-173-P0-01）：移除 API 批量任务处理分支。
API 批量任务由 api_task_worker 守护线程（_processor_loop，每 2s）唯一认领执行，
此前 APScheduler 轮询（本文件 _process_api_tasks）与守护线程并行认领同一任务，
且认领后 status 已置 running 导致本文件 _run_api_task 的
`status not in ("pending",)` 守卫直接 return —— 任务永久卡 running 无 stale 回收。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger("task_worker")

# ── 配置 ──
POLL_INTERVAL_SECONDS = 5
MAX_CONCURRENT_UI_RUNS = 2

_semaphore_ui = threading.Semaphore(MAX_CONCURRENT_UI_RUNS)


def poll_and_execute():
    """主轮询入口 — 由 APScheduler interval job 调用。
    检查 pending 状态的 UI 运行和蓝湖证据包任务。
    （Batch 174：API 批量任务已移交 api_task_worker 唯一处理）
    """
    reap_stale_ui_runs()
    _process_ui_runs()
    from app.services.lanhu_evidence.worker import poll_and_execute_evidence_jobs

    poll_and_execute_evidence_jobs()


def reap_stale_ui_runs() -> int:
    """回收失联的 UI 运行（Batch 181 / FIX-173-P2-06）。

    此前 UI run 无任何 stale 回收：worker 崩溃后 run 永久卡 running。
    阈值 30 分钟，远大于 Playwright 单任务 300s 超时，不会误杀长任务。
    best-effort：表缺失/DB 未迁移等环境问题不阻断轮询（CI 干净库无表场景）。
    """
    from app.core.db import SessionLocal
    from app.core.task_queue import QueueSpec, reap_stale
    from app.models.ui_test import UiTestRun

    db = SessionLocal()
    try:
        spec = QueueSpec(
            model=UiTestRun,
            status_col="status",
            pending="pending",
            running="running",
            failed="fail",
            lock_by_col="locked_by",
            lock_at_col="locked_at",
        )
        return reap_stale(db, spec, stale_seconds=30 * 60)
    except Exception:  # noqa: BLE001 - 维护性回收不允许拖垮轮询
        logger.warning("[task-worker] UI run stale reap failed (best-effort)", exc_info=True)
        return 0
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# UI 测试运行
# ═══════════════════════════════════════════════════════

def _process_ui_runs():
    """拉取 pending UI 测试运行并提交执行。"""
    if not _semaphore_ui.acquire(blocking=False):
        return

    try:
        from app.core.db import SessionLocal
        from app.models.ui_test import UiTestRun

        db = SessionLocal()
        try:
            run = db.query(UiTestRun).filter_by(status="pending").order_by(
                UiTestRun.started_at.asc()
            ).first()

            if not run:
                return

            logger.info(f"[task-worker] Picked up UI run #{run.id}")
            _run_ui_test(run.id, run.job_id)
        finally:
            db.close()
    except Exception:
        logger.exception("[task-worker] Error in UI run poll")
    finally:
        _semaphore_ui.release()


def _run_ui_test(run_id: int, job_id: int):
    """在独立线程中执行 UI Playwright 测试。"""
    def _runner():
        from app.core.db import SessionLocal
        from app.services.playwright_executor import run_playwright_test as _run_pw

        db = SessionLocal()
        try:
            from app.models.ui_test import UiTestJob, UiTestRun
            run = db.get(UiTestRun, run_id)
            job = db.get(UiTestJob, job_id)
            if not run or not job:
                return
            project_id = job.project_id
            _run_pw(db, run_id, job_id, project_id)
        except Exception:
            logger.exception(f"[task-worker] UI run #{run_id} crashed")
            try:
                from app.models.ui_test import UiTestRun, UiTestJob
                run = db.get(UiTestRun, run_id)
                if run:
                    run.status = "failed"
                    run.finished_at = datetime.now(timezone.utc)
                    run.error_message = "Worker 执行崩溃"
                job = db.get(UiTestJob, job_id)
                if job:
                    job.status = "failed"
                db.commit()
            except Exception:
                logger.warning("任务状态回写失败")
        finally:
            db.close()

    t = threading.Thread(target=_runner, daemon=True, name=f"ui-run-{run_id}")
    t.start()
