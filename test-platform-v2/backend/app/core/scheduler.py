"""APScheduler integration for cron-based test schedule execution."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _execute_schedule(schedule_id: int):
    """Callback fired by APScheduler when a cron trigger expires.
    Opens a dedicated DB session to avoid interfering with the request session.
    """
    from app.core.db import SessionLocal
    from app.models.test_schedule import TestSchedule, TestScheduleRun
    from app.services.test_plan_service import execute_all_cases
    from sqlalchemy import select

    db = SessionLocal()
    try:
        # Serialize the claim in PostgreSQL. SQLite also serializes the
        # following write transaction, which keeps the local profile honest.
        sched = db.scalar(
            select(TestSchedule)
            .where(TestSchedule.id == schedule_id)
            .with_for_update()
        )
        if not sched:
            logger.warning(f"[scheduler] Schedule #{schedule_id} not found, skipping")
            return {"triggered": False, "reason": "not_found"}

        active_run = db.scalar(
            select(TestScheduleRun)
            .where(
                TestScheduleRun.schedule_id == schedule_id,
                TestScheduleRun.status == "running",
            )
            .order_by(TestScheduleRun.id.desc())
        )
        if active_run:
            db.rollback()
            logger.info(
                "[scheduler] Schedule #%s already running as run #%s; duplicate trigger ignored",
                schedule_id,
                active_run.id,
            )
            return {
                "triggered": False,
                "reason": "already_running",
                "run_id": active_run.id,
            }

        run = TestScheduleRun(
            schedule_id=schedule_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()
        run_id = run.id
        db.commit()

        if sched.job_type == "ui":
            # B112-3：UI job 定时 —— 触发 UI job（Playwright 异步执行，schedule run 记录 ui_run_id）
            from app.services.ui_test_service import trigger_job as trigger_ui_job

            ui_run = trigger_ui_job(
                db,
                sched.job_id,
                sched.project_id,
                confirm_prod=True,
                has_trigger_prod=True,
            )
            result = {
                "ui_run_id": ui_run.get("id"),
                "status": ui_run.get("status"),
                "total": 1,
                "pass_": 0,
                "fail": 0,
                "skip": 0,
                "block": 0,
                "pending": 1,
            }
        elif sched.job_type == "report":
            # Batch 155 / P2-15：计划维度定时生成报告
            from app.schemas.test_report import ReportCreate
            from app.services.report_service import create_report

            if not sched.plan_id:
                raise ValueError("job_type=report 必须提供 plan_id")
            report = create_report(
                db,
                ReportCreate(plan_id=sched.plan_id, name=f"定时报告-{sched.name or sched.id}"),
                creator_id=0,
                project_id=sched.project_id,
            )
            result = {
                "report_id": report.get("report_id") or report.get("id") or "",
                "status": "completed",
                "total": 0,
                "pass_": 0,
                "fail": 0,
                "skip": 0,
                "block": 0,
                "pending": 0,
            }
        else:
            execution_result = execute_all_cases(
                db,
                sched.plan_id,
                executor_id=0,
                project_id=sched.project_id,
            )
            result = {
                "total": execution_result["total"],
                "pass_": execution_result["passed"],
                "fail": execution_result["failed"],
                "skip": execution_result["skipped"],
                "block": 0,
                "pending": 0,
            }
        run = db.get(TestScheduleRun, run_id)
        sched = db.get(TestSchedule, schedule_id)
        if run is None or sched is None:
            raise RuntimeError("调度运行记录在执行期间被删除")
        run.status = "completed"
        run.result = json.dumps(result, ensure_ascii=False)
        run.finished_at = datetime.now(timezone.utc)
        sched.last_run = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "[scheduler] Schedule #%s '%s' completed: %s",
            schedule_id,
            sched.name,
            result,
        )

        # Success notification is best-effort and cannot change the completed
        # execution result. notify_sync records its own delivery outcome.
        try:
            from app.services.notify_service import notify_sync

            _ndb = SessionLocal()
            try:
                if sched.job_type == "report":
                    notify_sync(
                        _ndb,
                        sched.project_id,
                        "report_generated",
                        {
                            "report_name": f"定时报告-{sched.name or sched.id}",
                            "pass_rate": "-",
                            "link": "/report",
                        },
                    )
                else:
                    notify_sync(
                        _ndb,
                        sched.project_id,
                        "plan_done",
                        {
                            "plan_name": sched.plan.name if sched.plan else sched.name,
                            "result_summary": (
                                f"通过 {result['pass_']} / 失败 {result['fail']} / "
                                f"跳过 {result['skip']}"
                            ),
                            "link": "",
                        },
                    )
            finally:
                _ndb.close()
        except Exception as notify_err:
            logger.warning(
                "[scheduler] Failed to send completion notification: %s",
                notify_err,
            )

        return {"triggered": True, "run_id": run_id, "result": result}

    except Exception as e:
        logger.exception(f"[scheduler] Schedule #{schedule_id} failed: {e}")
        db.rollback()
        try:
            if "run_id" in locals():
                failed_run = db.get(TestScheduleRun, run_id)
                if failed_run is None:
                    raise RuntimeError("调度失败后无法找到运行记录")
                failed_run.status = "failed"
                failed_run.error_message = str(e)[:500]
                failed_run.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.exception(
                "[scheduler] Failed to persist failure for schedule #%s",
                schedule_id,
            )

        # Fire notification on schedule failure (with a fresh session)
        try:
            failed_sched = db.get(TestSchedule, schedule_id)
            if failed_sched:
                from app.services.notify_service import notify_sync
                _ndb = SessionLocal()
                try:
                    notify_sync(
                        _ndb,
                        failed_sched.project_id,
                        "schedule_failed",
                        {
                            "schedule_name": failed_sched.name,
                            "error": str(e)[:200],
                            "link": "",
                        },
                    )
                finally:
                    _ndb.close()
        except Exception as notify_err:
            logger.warning(f"[scheduler] Failed to send failure notification: {notify_err}")
        return {
            "triggered": False,
            "reason": "execution_failed",
            "error": str(e)[:200],
        }
    finally:
        db.close()


def add_schedule_job(schedule_id: int, cron_expression: str):
    """Register a cron job for a schedule (idempotent)."""
    try:
        scheduler.add_job(
            func=_execute_schedule,
            trigger=CronTrigger.from_crontab(cron_expression),
            args=[schedule_id],
            id=f"schedule_{schedule_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info(f"[scheduler] Job added: schedule_{schedule_id} ({cron_expression})")
    except (ValueError, TypeError) as e:
        logger.error(f"[scheduler] Failed to add job schedule_{schedule_id}: {e}")


def remove_schedule_job(schedule_id: int):
    """Remove a cron job."""
    try:
        scheduler.remove_job(f"schedule_{schedule_id}")
        logger.info(f"[scheduler] Job removed: schedule_{schedule_id}")
    except Exception:
        pass  # job doesn't exist


def toggle_schedule_job(schedule_id: int, enabled: bool, cron_expression: str):
    """Enable or disable a schedule job."""
    if enabled:
        add_schedule_job(schedule_id, cron_expression)
    else:
        remove_schedule_job(schedule_id)


def init_scheduler():
    """Called at app startup. Loads all enabled schedules from DB and registers jobs."""
    from app.core.db import SessionLocal
    from app.models.test_schedule import TestSchedule
    from sqlalchemy import select

    scheduler.start()
    logger.info("[scheduler] BackgroundScheduler started")

    db = SessionLocal()
    try:
        schedules = db.execute(
            select(TestSchedule).where(TestSchedule.enabled)
        ).scalars().all()

        for s in schedules:
            try:
                add_schedule_job(s.id, s.cron_expression)
            except Exception as e:
                logger.error(f"[scheduler] Failed to load schedule #{s.id}: {e}")

        logger.info(f"[scheduler] Loaded {len(schedules)} enabled schedules")
    finally:
        db.close()

    # ── 注册独立任务 Worker 轮询 ──
    from app.services.task_worker import poll_and_execute
    from apscheduler.triggers.interval import IntervalTrigger
    try:
        scheduler.add_job(
            func=poll_and_execute,
            trigger=IntervalTrigger(seconds=5),
            id="task_worker_poll",
            replace_existing=True,
        )
        logger.info("[scheduler] Task worker poll registered (every 5s)")
    except Exception as e:
        logger.error(f"[scheduler] Failed to register task worker: {e}")

    # ── 知识保鲜退化 + 自动归档（每天凌晨 3:00）──
    try:
        from app.services.knowledge.source_service import decay_freshness_in_new_session
        scheduler.add_job(
            func=decay_freshness_in_new_session,
            trigger=CronTrigger(hour=3, minute=7),
            id="knowledge_freshness_decay",
            replace_existing=True,
        )
        logger.info("[scheduler] Knowledge freshness decay registered (daily 03:07)")
    except Exception as e:
        logger.error(f"[scheduler] Failed to register freshness decay: {e}")

    # ── 概念地图自演化（每天凌晨 4:00）──
    try:
        from app.services.knowledge.entity_service import evolve_graph_in_new_session
        from app.core.config import settings
        if settings.knowledge_graph_enabled:
            def _evolve_all_projects():
                from app.core.db import SessionLocal
                from app.models.knowledge import KnowledgeEntity
                from sqlalchemy import select
                db = SessionLocal()
                try:
                    pids = list(db.scalars(
                        select(KnowledgeEntity.project_id).distinct()
                    ).all())
                    for pid in pids:
                        try:
                            evolve_graph_in_new_session(pid)
                        except Exception as ex:
                            logger.error(f"[scheduler] Graph evolve failed for project {pid}: {ex}")
                finally:
                    db.close()

            scheduler.add_job(
                func=_evolve_all_projects,
                trigger=CronTrigger(hour=4, minute=13),
                id="knowledge_graph_evolve",
                replace_existing=True,
            )
            logger.info("[scheduler] Knowledge graph auto-evolution registered (daily 04:13)")
    except Exception as e:
        logger.error(f"[scheduler] Failed to register graph evolution: {e}")


def shutdown_scheduler():
    """Called at app shutdown."""
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] BackgroundScheduler shut down")
