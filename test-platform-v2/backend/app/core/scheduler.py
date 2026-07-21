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
    from app.models.test_plan import TestPlanCase
    from app.models.test_schedule import TestSchedule, TestScheduleRun
    from sqlalchemy import select

    db = SessionLocal()
    try:
        sched = db.scalar(select(TestSchedule).where(TestSchedule.id == schedule_id))
        if not sched:
            logger.warning(f"[scheduler] Schedule #{schedule_id} not found, skipping")
            return

        # Create a run record
        run = TestScheduleRun(
            schedule_id=schedule_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        total_cases_count = 0
        pass_count = 0
        fail_count = 0
        skip_count = 0
        block_count = 0
        pending_count = 0

        # Get all plan cases and create execution records
        pcases = db.execute(
            select(TestPlanCase).where(TestPlanCase.plan_id == sched.plan_id)
        ).scalars().all()

        # Import here to avoid circular imports
        from app.models.test_plan import TestExecution

        for pc in pcases:
            total_cases_count += 1
            status = "pending"
            # Create an execution record
            exec_ = TestExecution(
                plan_case_id=pc.id,
                executor_id=0,  # system
                status=status,
                actual_result="",
                notes=f"[定时任务自动执行] schedule #{schedule_id}",
            )
            db.add(exec_)
            pending_count += 1

        db.flush()

        # Update run record
        result = {
            "total": total_cases_count,
            "pass_": pass_count,
            "fail": fail_count,
            "skip": skip_count,
            "block": block_count,
            "pending": pending_count,
        }
        run.status = "completed"
        run.result = json.dumps(result, ensure_ascii=False)
        run.finished_at = datetime.now(timezone.utc)

        # Update schedule
        sched.last_run = datetime.now(timezone.utc)

        db.commit()
        logger.info(
            f"[scheduler] Schedule #{schedule_id} '{sched.name}' completed: "
            f"{total_cases_count} cases queued"
        )

    except Exception as e:
        logger.exception(f"[scheduler] Schedule #{schedule_id} failed: {e}")
        try:
            if 'run' in locals():
                run.status = "failed"
                run.error_message = str(e)[:500]
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass

        # Fire notification on schedule failure (with a fresh session)
        try:
            if 'sched' in locals() and sched:
                from app.services.notify_service import notify_sync
                _ndb = SessionLocal()
                try:
                    notify_sync(
                        _ndb,
                        sched.project_id,
                        "schedule_failed",
                        {
                            "schedule_name": sched.name,
                            "error": str(e)[:200],
                            "link": "",
                        },
                    )
                finally:
                    _ndb.close()
        except Exception as notify_err:
            logger.warning(f"[scheduler] Failed to send failure notification: {notify_err}")
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
            select(TestSchedule).where(TestSchedule.enabled == True)
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


def shutdown_scheduler():
    """Called at app shutdown."""
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] BackgroundScheduler shut down")
