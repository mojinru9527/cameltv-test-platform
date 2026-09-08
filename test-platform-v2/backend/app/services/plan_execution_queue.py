"""Persist-before-ack plan dispatch; lost running work is never automatically replayed."""
import json
import logging
import threading
import uuid

from sqlalchemy import select, update

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.task_queue import QueueSpec, QueueWorkerLoop, atomic_claim, utcnow
from app.models.plan_execution_job import PlanExecutionJob
from app.models.test_plan import TestPlan

logger = logging.getLogger(__name__)
SPEC = QueueSpec(model=PlanExecutionJob)
_loop = QueueWorkerLoop(name='plan-execution-worker', poll_interval=2, on_tick=lambda: poll_once())


def enqueue(db, *, plan_id, project_id, executor_id, environment_id, ui_environment_id, auto_ui):
    plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id))
    if plan is None:
        raise ValueError('Plan does not exist in this project')
    request = dict(plan_id=plan_id, project_id=project_id, executor_id=executor_id,
                   environment_id=environment_id, ui_environment_id=ui_environment_id, auto_ui=auto_ui)
    job = PlanExecutionJob(plan_id=plan_id, project_id=project_id, creator_id=executor_id,
                           request_json=json.dumps(request))
    db.add(job)
    db.commit()
    db.refresh(job)
    _loop.kick()
    return job.id


def list_jobs(db, plan_id, project_id):
    rows = db.scalars(select(PlanExecutionJob).where(
        PlanExecutionJob.plan_id == plan_id, PlanExecutionJob.project_id == project_id,
    ).order_by(PlanExecutionJob.id.desc()).limit(50)).all()
    return [dict(id=row.id, plan_id=row.plan_id, status=row.status,
                 result=json.loads(row.result_json), error_message=row.error_message,
                 created_at=row.created_at, started_at=row.started_at, finished_at=row.finished_at)
            for row in rows]


def ensure_processor_running():
    if settings.worker_execution_enabled:
        _loop.start()


def shutdown_processor():
    _loop.shutdown()


def _owned(job_id, owner):
    return (PlanExecutionJob.id == job_id, PlanExecutionJob.status == 'running',
            PlanExecutionJob.locked_by == owner)


def _heartbeat(job_id, owner, stop):
    while not stop.wait(15):
        try:
            with SessionLocal() as db:
                result = db.execute(update(PlanExecutionJob).where(*_owned(job_id, owner)).values(locked_at=utcnow()))
                db.commit()
                if result.rowcount != 1:
                    return
        except Exception:
            logger.exception('Plan dispatch heartbeat failed job=%s', job_id)


def poll_once():
    if not settings.worker_execution_enabled:
        return
    owner = uuid.uuid4().hex
    with SessionLocal() as db:
        job = atomic_claim(db, SPEC, worker_id=owner)
        if job is None:
            return
        job_id, request = job.id, json.loads(job.request_json)
    stop = threading.Event()
    heartbeat = threading.Thread(target=_heartbeat, args=(job_id, owner, stop), daemon=True,
                                 name='plan-execution-heartbeat')
    heartbeat.start()
    status, result_json, error = 'completed', '{}', ''
    try:
        from app.services.test_plan_service import execute_all_cases
        with SessionLocal() as db:
            result_json = json.dumps(execute_all_cases(db, **request), default=str)
    except Exception as exc:
        logger.exception('Plan execution failed job=%s', job_id)
        status, error = 'failed', str(exc)[:2000]
    finally:
        stop.set()
        heartbeat.join(timeout=20)
        with SessionLocal() as db:
            db.execute(update(PlanExecutionJob).where(*_owned(job_id, owner)).values(
                status=status, result_json=result_json, error_message=error,
                finished_at=utcnow(), locked_by='',
            ))
            db.commit()
