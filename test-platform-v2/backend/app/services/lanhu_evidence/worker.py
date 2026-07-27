"""Persistent polling worker for recoverable Lanhu evidence jobs."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.lanhu_evidence import LanhuEvidenceJob


logger = logging.getLogger("lanhu_evidence_worker")
_semaphore = threading.BoundedSemaphore(
    max(1, int(settings.lanhu_evidence_max_concurrent)),
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
    """Atomically transition the oldest pending job to running."""
    candidate = db.scalar(
        select(LanhuEvidenceJob.id)
        .where(LanhuEvidenceJob.status == "pending")
        .order_by(LanhuEvidenceJob.id)
        .limit(1)
    )
    if candidate is None:
        return None
    now = datetime.now()
    updated = db.execute(
        update(LanhuEvidenceJob)
        .where(
            LanhuEvidenceJob.id == candidate,
            LanhuEvidenceJob.status == "pending",
        )
        .values(
            status="running",
            stage="discovering",
            heartbeat_at=now,
            started_at=now,
        )
    )
    db.commit()
    if updated.rowcount != 1:
        return None
    return db.get(LanhuEvidenceJob, candidate)


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
