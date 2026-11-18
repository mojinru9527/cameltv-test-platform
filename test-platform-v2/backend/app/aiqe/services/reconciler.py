"""AUD-006：Reconciler（过期租约回收、Run 收口、实验同步）。

v1.5 §01 AUD-006 技术机制 6–7：

- 扫描过期 Job、无 heartbeat NodeRun、节点终态但 Run 未收口、Run 终态但
  Regression/Experiment 未同步；
- 自动恢复有次数限制、退避、审计和人工介入门槛；
- 目标：Worker kill 后 Run 在 SLA 内收敛到正确终态或 UNKNOWN，**不永久 RUNNING**。

本模块是**确定性**的：只根据数据库事实做收敛，不做任何推测性定责。
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import dag_scheduler
from app.aiqe.services import lease as lease_service
from app.models.execution_job import ExecutionJob

logger = logging.getLogger(__name__)

DEFAULT_REQUEUE_LIMIT = 3
_stop = threading.Event()
_thread: threading.Thread | None = None


@dataclass
class ReconcileReport:
    scanned_jobs: int = 0
    expired_jobs: list[int] = field(default_factory=list)
    requeued_nodes: list[str] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    finalized_runs: list[dict] = field(default_factory=list)
    experiments_synced: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {
            "scanned_jobs": self.scanned_jobs,
            "expired_jobs": list(self.expired_jobs),
            "requeued_nodes": list(self.requeued_nodes),
            "blocked_nodes": list(self.blocked_nodes),
            "finalized_runs": list(self.finalized_runs),
            "experiments_synced": list(self.experiments_synced),
            "errors": list(self.errors),
        }


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _payload_of(job: ExecutionJob) -> dict:
    import json

    try:
        return json.loads(job.payload_json or "{}")
    except (TypeError, ValueError):
        return {}


def _reconcile_expired_jobs(
    db: Session, report: ReconcileReport, now: datetime, *, requeue_limit: int
) -> None:
    rows = list(
        db.scalars(
            select(ExecutionJob).where(
                ExecutionJob.status == "running",
                ExecutionJob.lease_expires_at.isnot(None),
                ExecutionJob.lease_expires_at < now,
            )
        )
    )
    report.scanned_jobs += len(rows)
    for job in rows:
        payload = _payload_of(job)
        node_run_id = str(payload.get("node_run_id") or "")
        run_id = str(payload.get("run_id") or "")
        node = db.scalar(select(NodeRun).where(NodeRun.id == node_run_id)) if node_run_id else None

        job.status = "expired"
        job.error_message = "LEASE_EXPIRED"
        job.finished_at = now
        report.expired_jobs.append(int(job.id))

        if node is None or not run_id:
            continue
        # 先提升 token，确保旧 Worker 之后的迟到上报一定被拒。
        try:
            lease_service.bump_fencing_token(
                db, node.id, token=int(job.attempt or 0) + 1
            )
        except LookupError:
            pass

        if node.status in {"RUNNING", "READY"}:
            attempts = int(node.attempt_count or 0)
            run = db.get(TestRun, run_id)
            if attempts < requeue_limit and run is not None and run.status == "RUNNING":
                node.status = "PENDING"
                node.started_at = None
                node.finished_at = None
                node.error_class = ""
                node.execution_job_id = None
                report.requeued_nodes.append(node.node_key)
                dag_scheduler.emit_event(
                    db,
                    run_id=run_id,
                    event_type="node.lease_expired",
                    payload={
                        "node_key": node.node_key,
                        "attempt": attempts,
                        "action": "requeued",
                    },
                    producer_event_id=f"{node.id}:{attempts}:node.lease_expired",
                    node_run_id=node.id,
                )
            else:
                node.status = "BLOCKED"
                node.error_class = "LEASE_EXPIRED"
                node.finished_at = now
                report.blocked_nodes.append(node.node_key)
                dag_scheduler.emit_event(
                    db,
                    run_id=run_id,
                    event_type="node.lease_expired",
                    payload={
                        "node_key": node.node_key,
                        "attempt": attempts,
                        "action": "blocked",
                    },
                    producer_event_id=f"{node.id}:{attempts}:node.lease_expired",
                    node_run_id=node.id,
                )
    db.flush()


def _reconcile_runs(db: Session, report: ReconcileReport) -> None:
    runs = list(db.scalars(select(TestRun).where(TestRun.status == "RUNNING")))
    for run in runs:
        rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
        if not rows:
            continue
        if any(node.status not in dag_scheduler.NODE_TERMINAL for node in rows):
            continue
        before = run.status
        dag_scheduler.finalize_run(db, run.id)
        if run.status != before:
            report.finalized_runs.append(
                {
                    "run_id": run.id,
                    "status": run.status,
                    "outcome": run.outcome,
                }
            )
    db.flush()


def _reconcile_experiments(db: Session, report: ReconcileReport) -> None:
    from app.aiqe.models.triage import TriageExperiment
    from app.aiqe.services import triage_service

    rows = list(
        db.scalars(
            select(TriageExperiment).where(
                TriageExperiment.status.in_(["QUEUED", "RUNNING", "VALIDATED"])
            )
        )
    )
    for row in rows:
        try:
            before = row.status
            triage_service.sync_experiment_result(db, row.id)
            if row.status != before:
                report.experiments_synced.append(row.id)
        except Exception as exc:  # 单个实验失败不能中断整轮收敛
            report.errors.append(f"experiment {row.id}: {type(exc).__name__}: {exc}")
    db.flush()


def reconcile(
    db: Session,
    *,
    now: datetime | None = None,
    requeue_limit: int = DEFAULT_REQUEUE_LIMIT,
    sync_experiments: bool = True,
) -> ReconcileReport:
    """单轮收敛；调用方负责 ``db.commit()``。"""
    moment = now or _now()
    report = ReconcileReport()
    _reconcile_expired_jobs(db, report, moment, requeue_limit=requeue_limit)
    _reconcile_runs(db, report)
    if sync_experiments:
        _reconcile_experiments(db, report)
    return report


def start_reconciler(poll_seconds: float | None = None) -> None:
    """可选后台线程（``AIQE_RECONCILER_ENABLED=true`` 时由 lifespan 启动）。"""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    from app.core.config import settings
    from app.core.db import SessionLocal

    interval = float(poll_seconds or settings.aiqe_reconciler_poll_seconds)
    _stop.clear()

    def loop() -> None:
        while not _stop.is_set():
            db = SessionLocal()
            try:
                reconcile(db)
                db.commit()
            except Exception:  # 线程不能退出
                db.rollback()
                logger.exception("aiqe reconciler loop error")
            finally:
                db.close()
            _stop.wait(max(0.5, interval))

    _thread = threading.Thread(target=loop, name="aiqe-reconciler", daemon=True)
    _thread.start()
    logger.info("aiqe reconciler started")


def stop_reconciler() -> None:
    global _thread
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=5)
        _thread = None


__all__ = [
    "DEFAULT_REQUEUE_LIMIT",
    "ReconcileReport",
    "reconcile",
    "start_reconciler",
    "stop_reconciler",
]
