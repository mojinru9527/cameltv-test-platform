"""独立任务 Worker — 轮询 pending 任务并执行，替代 BackgroundTasks。

特性：
- 轮询间隔可配（默认 5 秒）
- 并发上限控制
- 服务重启后 pending 任务自动恢复
- 同时处理 API 执行任务、UI 测试运行和蓝湖证据包任务
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger("task_worker")

# ── 配置 ──
POLL_INTERVAL_SECONDS = 5
MAX_CONCURRENT_API_TASKS = 3
MAX_CONCURRENT_UI_RUNS = 2

_semaphore_api = threading.Semaphore(MAX_CONCURRENT_API_TASKS)
_semaphore_ui = threading.Semaphore(MAX_CONCURRENT_UI_RUNS)


def poll_and_execute():
    """主轮询入口 — 由 APScheduler interval job 调用。
    检查 pending 状态的 API 任务、UI 运行和蓝湖证据包任务。
    """
    _process_api_tasks()
    _process_ui_runs()
    from app.services.lanhu_evidence.worker import poll_and_execute_evidence_jobs

    poll_and_execute_evidence_jobs()


# ═══════════════════════════════════════════════════════
# API 执行任务
# ═══════════════════════════════════════════════════════

def _process_api_tasks():
    """拉取 pending API 执行任务并提交执行。"""
    if not _semaphore_api.acquire(blocking=False):
        return  # 已达并发上限

    try:
        from app.core.db import SessionLocal
        from app.models.api_asset import ApiExecutionTask

        db = SessionLocal()
        try:
            task = db.query(ApiExecutionTask).filter_by(status="pending").order_by(
                ApiExecutionTask.created_at.asc()
            ).first()

            if not task:
                return

            logger.info(f"[task-worker] Picked up API task #{task.id} '{task.name}'")
            _run_api_task(task.id, task.project_id)
        finally:
            db.close()
    except Exception:
        logger.exception("[task-worker] Error in API task poll")
    finally:
        _semaphore_api.release()


def _run_api_task(task_db_id: int, project_id: int):
    """在独立线程中执行 API 批量任务。"""
    def _runner():
        from app.core.db import SessionLocal
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase
        from app.services.api_execution_service import execute_api_case
        import json

        db = SessionLocal()
        try:
            task = db.get(ApiExecutionTask, task_db_id)
            if not task or task.status not in ("pending",):
                return

            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            db.commit()

            items = db.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
            passed = 0
            failed = 0
            skipped = 0

            for item in items:
                # 取消检查
                db.refresh(task)
                if task.status == "cancelled":
                    item.status = "skipped"
                    item.error_message = "任务已取消"
                    skipped += 1
                    db.commit()
                    continue

                try:
                    result = execute_api_case(
                        db, item.case_id,
                        project_id=project_id,
                        environment_id=task.environment_id,
                    )
                    item.status = "passed" if result.get("all_pass", False) else "failed"
                    item.duration_ms = result.get("duration_ms", 0)
                    item.request_snapshot = json.dumps(result.get("request_snapshot", {}), ensure_ascii=False)
                    item.response_snapshot = _build_resp_snapshot(result)
                    item.assertion_results = json.dumps(result.get("assertions", []), ensure_ascii=False)
                    if result.get("error"):
                        item.error_message = result["error"]

                    if item.status == "passed":
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    item.status = "failed"
                    item.error_message = str(e)
                    failed += 1

            task.passed = passed
            task.failed = failed
            task.skipped = task.total - passed - failed + skipped
            task.status = "success" if (failed == 0 and skipped == 0) else ("failed" if failed > 0 else "cancelled")
            task.finished_at = datetime.now(timezone.utc)
            db.commit()

            if failed > 0:
                from app.services.knowledge import ingest_service
                ingest_service.ingest_execution_failure_in_new_session(project_id, task_db_id)

        except Exception:
            logger.exception(f"[task-worker] API task #{task_db_id} crashed")
        finally:
            db.close()

    t = threading.Thread(target=_runner, daemon=True, name=f"api-task-{task_db_id}")
    t.start()


def _build_resp_snapshot(result: dict) -> str:
    import json
    snapshot = result.get("response_snapshot", {})
    if not snapshot:
        raw_body = result.get("raw_body") or ""
        body_str = result.get("response_body") or raw_body
        body_size = len(str(body_str)) if body_str else 0
        snapshot = {
            "status_code": result.get("status_code"),
            "headers": result.get("response_headers", {}),
            "body_size_bytes": body_size,
            "truncated": False,
            "content_type": "",
        }
    return json.dumps(snapshot, ensure_ascii=False, default=str)


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
                    run.status = "fail"
                    run.finished_at = datetime.now(timezone.utc)
                    run.error_message = "Worker 执行崩溃"
                job = db.get(UiTestJob, job_id)
                if job:
                    job.status = "fail"
                db.commit()
            except Exception:
                pass
        finally:
            db.close()

    t = threading.Thread(target=_runner, daemon=True, name=f"ui-run-{run_id}")
    t.start()
