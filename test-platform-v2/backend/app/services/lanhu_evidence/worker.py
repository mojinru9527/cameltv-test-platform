"""Persistent polling worker for recoverable Lanhu evidence jobs.

Batch 181（FIX-173-P2-06）：认领改走 app.core.task_queue 统一原子原语
（条件 UPDATE + rowcount）；活性判定仍以 heartbeat_at 为准（job_runner 心跳线程
持续刷新），失联回收保留原 COALESCE 回落语义（heartbeat→started→updated→created）。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.task_queue import QueueSpec, atomic_claim, utcnow
from app.models.lanhu_evidence import LanhuEvidenceJob


logger = logging.getLogger("lanhu_evidence_worker")
_semaphore = threading.BoundedSemaphore(
    max(1, int(settings.lanhu_evidence_max_concurrent)),
)

# Batch 181：证据包队列契约——liveness 用 heartbeat_at（job_runner 心跳线程刷新）
_EVIDENCE_QUEUE = QueueSpec(
    model=LanhuEvidenceJob,
    id_col="id",
    status_col="status",
    pending="pending",
    running="running",
    failed="failed",
    lock_by_col="locked_by",
    lock_at_col="locked_at",
    liveness_col="heartbeat_at",
    order_col="id",
    order_asc=True,
)


def recover_stale_jobs(db: Session, stale_after_seconds: int) -> int:
    """Fail running jobs whose last durable liveness signal is stale."""
    cutoff = datetime.now() - timedelta(seconds=max(1, stale_after_seconds))
    last_seen = func.coalesce(
        LanhuEvidenceJob.heartbeat_at,
        LanhuEvidenceJob.started_at,
        LanhuEvidenceJob.updated_at,
        LanhuEvidenceJob.created_at,
    )
    result = db.execute(
        update(LanhuEvidenceJob)
        .where(
            LanhuEvidenceJob.status == "running",
            last_seen < cutoff,
        )
        .values(
            status="failed",
            stage="done",
            error_message="worker_lost",
            finished_at=datetime.now(),
        )
    )
    db.commit()
    return int(result.rowcount or 0)


def claim_next_job(db: Session) -> LanhuEvidenceJob | None:
    """Atomically transition the oldest pending job to running (Batch 181 统一原语).

    claim 同时写 heartbeat_at 与 locked_by/locked_at，锁语义与其他队列一致；
    心跳线程（job_runner）在运行期间持续刷新 heartbeat_at。
    """
    job = atomic_claim(
        db,
        _EVIDENCE_QUEUE,
        worker_id="lanhu-worker",
        stale_seconds=settings.lanhu_evidence_stale_after_seconds,
    )
    if job is None:
        return None
    # 保留原语义：认领即进入 discovering 阶段并打心跳
    now = datetime.now()
    job.stage = "discovering"
    job.heartbeat_at = now
    if job.started_at is None:
        job.started_at = now
    db.commit()
    return db.get(LanhuEvidenceJob, job.id)


def poll_and_execute_evidence_jobs() -> None:
    """Recover stale work, claim one job, and execute it outside the poller."""
    if not settings.lanhu_evidence_worker_enabled:
        return

    db = SessionLocal()
    try:
        recover_stale_jobs(db, settings.lanhu_evidence_stale_after_seconds)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Failed to recover stale Lanhu evidence jobs")
    finally:
        db.close()

    if not _semaphore.acquire(blocking=False):
        return

    job_id: int | None = None
    project_id = 0
    db = SessionLocal()
    try:
        claimed = claim_next_job(db)
        if claimed is not None:
            job_id = claimed.id
            project_id = claimed.project_id
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Failed to claim a Lanhu evidence job")
    finally:
        db.close()

    if job_id is None:
        _semaphore.release()
        return

    def _runner() -> None:
        try:
            from app.services.lanhu_evidence.job_runner import run_job_in_new_session

            run_job_in_new_session(job_id, project_id)
        except Exception:  # noqa: BLE001
            logger.exception("Lanhu evidence job #%s worker crashed", job_id)
        finally:
            _semaphore.release()

    thread = threading.Thread(
        target=_runner,
        daemon=True,
        name=f"lanhu-evidence-{job_id}",
    )
    try:
        thread.start()
    except Exception:
        _semaphore.release()
        raise
