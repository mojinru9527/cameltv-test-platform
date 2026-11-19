"""v1.4 FIX-006：Job / NodeRun / TestRun 状态对账（reconciler）。

解决"Job FAILED 但 NodeRun/TestRun 永远 RUNNING"与过期租约悬挂：
- 节点 READY/RUNNING 但 Job 丢失/失败/取消/租约过期 → 收敛为 ERROR/BLOCKED/FAILED；
- 所有节点终态但 Run 仍 RUNNING → 按事实收口 COMPLETED（PASS/FAIL/INCOMPLETE）；
- Run 没有任何节点且超时 → ERROR；
- COMPLETED 无 outcome → ERROR（违反状态机）。
所有收敛写 RunEvent，幂等（producer_event_id）。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services.event_service import append_event
from app.aiqe.services.run_state import apply_transition
from app.models.execution_job import ExecutionJob

NODE_TERMINAL = frozenset({"PASSED", "FAILED", "BLOCKED", "SKIPPED", "CANCELED", "ERROR"})
NODE_FAILED = frozenset({"FAILED", "ERROR", "TIMED_OUT"})


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _event(db: Session, run_id: str, event_type: str, payload: dict, *, key: str) -> None:
    append_event(
        db,
        run_id=run_id,
        event_type=event_type,
        payload={"schema_version": "1.0", **payload},
        producer="system",
        producer_event_id=key,
    )


def _latest_attempt(db: Session, node: NodeRun) -> StepAttempt | None:
    return db.scalar(
        select(StepAttempt)
        .where(StepAttempt.node_run_id == node.id)
        .order_by(StepAttempt.attempt_no.desc())
    )


def _close_node(
    db: Session,
    node: NodeRun,
    status: str,
    error_class: str,
    reason: str,
) -> None:
    if node.status in NODE_TERMINAL:
        return
    node.status = status
    node.error_class = error_class
    node.finished_at = _now()
    attempt = _latest_attempt(db, node)
    if attempt is not None and attempt.status not in {"PASSED", "FAILED", "BLOCKED", "SKIPPED", "CANCELED", "ERROR"}:
        attempt.status = status
        attempt.finished_at = _now()
        attempt.error_json = {"class": error_class, "reason": reason}
    db.flush()


def _finalize_run(db: Session, run: TestRun, nodes: list[NodeRun]) -> None:
    # V16-005：QUEUED 悬挂 Run 与 RUNNING Run 一样需要收敛。
    if run.status not in {"RUNNING", "QUEUED"} or not nodes:
        return
    if any(node.status not in NODE_TERMINAL for node in nodes):
        return
    if run.status == "QUEUED":
        # 从未真正执行的 Run 没有 outcome 语义，按 ERROR 收敛（可告警、可重跑）。
        apply_transition(run, "ERROR")
        run.finished_at = _now()
        _event(
            db,
            run.id,
            "run.reconciled",
            {"status": run.status, "reason": "QUEUED_WITHOUT_JOB"},
            key=f"run-reconciled:{run.id}:QUEUED:ERROR",
        )
        db.flush()
        return
    statuses = {node.node_key: node.status for node in nodes}
    if any(status in NODE_FAILED for status in statuses.values()):
        apply_transition(run, "COMPLETED", outcome="FAIL")
    elif any(status in {"BLOCKED", "ERROR"} for status in statuses.values()):
        apply_transition(run, "COMPLETED", outcome="INCOMPLETE")
    else:
        apply_transition(run, "COMPLETED", outcome="PASS")
    run.finished_at = _now()
    _event(
        db,
        run.id,
        "run.reconciled",
        {"status": run.status, "outcome": run.outcome},
        key=f"run-reconciled:{run.id}:{run.status}:{run.outcome}",
    )
    db.flush()


@dataclass
class ReconcileReport:
    """AUD-006 对账报告；同时保留 v1.4 统计键的 dict 访问。"""

    scanned_jobs: int = 0
    expired_jobs: list[int] = field(default_factory=list)
    requeued_nodes: list[str] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    finalized_runs: list[dict] = field(default_factory=list)
    experiments_synced: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    runs_scanned: int = 0
    nodes_closed: int = 0
    jobs_failed: int = 0
    runs_completed: int = 0
    secrets_purged: int = 0
    outbox_published: int = 0
    outbox_failed: int = 0

    def payload(self) -> dict[str, Any]:
        return {
            "scanned_jobs": self.scanned_jobs,
            "expired_jobs": list(self.expired_jobs),
            "requeued_nodes": list(self.requeued_nodes),
            "blocked_nodes": list(self.blocked_nodes),
            "finalized_runs": list(self.finalized_runs),
            "experiments_synced": list(self.experiments_synced),
            "errors": list(self.errors),
            "runs_scanned": self.runs_scanned,
            "nodes_closed": self.nodes_closed,
            "jobs_failed": self.jobs_failed,
            "runs_completed": self.runs_completed,
        }

    def __getitem__(self, key: str) -> Any:
        return self.payload()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload().get(key, default)


def reconcile(
    db: Session,
    *,
    stale_seconds: int | None = None,
    limit: int = 200,
    requeue_limit: int = 3,
    sync_experiments: bool = True,
) -> ReconcileReport:
    """对账 RUNNING Run / 过期租约；返回 ReconcileReport（兼容 dict 访问）。"""
    stale = max(30, int(stale_seconds or 900))
    cutoff = _now() - timedelta(seconds=stale)
    runs = list(
        db.scalars(
            select(TestRun)
            # V16-005：QUEUED 长时间没有 Job 也属于悬挂状态，必须收敛并告警。
            .where(TestRun.status.in_(("RUNNING", "QUEUED")))
            .order_by(TestRun.created_at)
            .limit(max(1, int(limit)))
        )
    )
    stats = ReconcileReport(runs_scanned=len(runs))
    for run in runs:
        nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
        if not nodes:
            _event(
                db,
                run.id,
                "run.orphan",
                {"reason": "no_node_runs"},
                key=f"run-orphan:{run.id}",
            )
            apply_transition(run, "ERROR")
            run.finished_at = _now()
            stats.runs_completed += 1
            continue
        for node in nodes:
            if node.status in NODE_TERMINAL:
                continue
            job = db.get(ExecutionJob, node.execution_job_id) if node.execution_job_id else None
            if job is None:
                # READY 且从未派发：超过阈值才判 BLOCKED，避免与调度竞态。
                started = _aware(node.started_at)
                if started is not None and started > cutoff:
                    continue
                _close_node(db, node, "ERROR", "JOB_MISSING", "ExecutionJob 不存在")
                _event(
                    db,
                    run.id,
                    "node.reconciled",
                    {"node_key": node.node_key, "status": "ERROR", "reason": "JOB_MISSING"},
                    key=f"node-reconciled:{node.id}:JOB_MISSING",
                )
                stats.nodes_closed += 1
                continue
            heartbeat = _aware(job.heartbeat_at) or _aware(job.claimed_at)
            lease = _aware(job.lease_expires_at)
            expired = (lease is not None and lease < _now()) or (
                heartbeat is not None and heartbeat < cutoff
            )
            if job.status in {"failed", "canceled"}:
                status = "FAILED" if job.status == "failed" else "CANCELED"
                _close_node(
                    db,
                    node,
                    status,
                    "JOB_FAILED" if status == "FAILED" else "JOB_CANCELED",
                    job.error_message or job.status,
                )
                _event(
                    db,
                    run.id,
                    "node.reconciled",
                    {
                        "node_key": node.node_key,
                        "status": status,
                        "job_id": job.id,
                        "reason": job.status,
                    },
                    key=f"node-reconciled:{node.id}:{job.id}:{job.status}",
                )
                stats.nodes_closed += 1
                continue
            if job.status == "running" and expired:
                # AUD-006：租约过期 → 提升 fencing token；未超过上限则重排，否则 BLOCKED。
                job.status = "expired"
                job.error_message = "LEASE_EXPIRED"
                job.finished_at = _now()
                stats.scanned_jobs += 1
                stats.expired_jobs.append(int(job.id))
                try:
                    from app.aiqe.services import lease as lease_service

                    lease_service.bump_fencing_token(
                        db, node.id, token=int(job.attempt or 0) + 1
                    )
                except (LookupError, Exception):
                    pass
                attempts = int(node.attempt_count or 0)
                if attempts < int(requeue_limit) and run.status == "RUNNING":
                    node.status = "PENDING"
                    node.started_at = None
                    node.finished_at = None
                    node.error_class = ""
                    node.execution_job_id = None
                    stats.requeued_nodes.append(node.node_key)
                    _event(
                        db,
                        run.id,
                        "node.lease_expired",
                        {"node_key": node.node_key, "attempt": attempts, "action": "requeued"},
                        key=f"node-lease-expired:{node.id}:{attempts}",
                    )
                else:
                    _close_node(db, node, "BLOCKED", "LEASE_EXPIRED", "Runner 租约过期")
                    stats.blocked_nodes.append(node.node_key)
                    _event(
                        db,
                        run.id,
                        "node.lease_expired",
                        {"node_key": node.node_key, "attempt": attempts, "action": "blocked"},
                        key=f"node-lease-expired:{node.id}:{attempts}",
                    )
                stats.nodes_closed += 1
                stats.jobs_failed += 1
                continue
            if job.status == "pending":
                created = _aware(job.created_at)
                if created is not None and created < cutoff:
                    # 长时间无人认领：不是业务失败，节点 BLOCKED，等待人工/调度补偿。
                    _close_node(db, node, "BLOCKED", "NODE_UNAVAILABLE", "Job 长时间无人认领")
                    _event(
                        db,
                        run.id,
                        "node.reconciled",
                        {
                            "node_key": node.node_key,
                            "status": "BLOCKED",
                            "job_id": job.id,
                            "reason": "NODE_UNAVAILABLE",
                        },
                        key=f"node-reconciled:{node.id}:{job.id}:NODE_UNAVAILABLE",
                    )
                    stats.nodes_closed += 1
        before = run.status
        _finalize_run(db, run, nodes)
        if before == "RUNNING" and run.status == "COMPLETED":
            stats.runs_completed += 1
            stats.finalized_runs.append(
                {"run_id": run.id, "status": run.status, "outcome": run.outcome}
            )

    # COMPLETED 无 outcome 是非法状态，必须收敛为 ERROR（不能继续被当作 PASS）。
    invalid = list(
        db.scalars(
            select(TestRun).where(
                TestRun.status == "COMPLETED", TestRun.outcome.is_(None)
            )
        )
    )
    for run in invalid:
        run.status = "ERROR"
        _event(
            db,
            run.id,
            "run.reconciled",
            {"reason": "COMPLETED_WITHOUT_OUTCOME"},
            key=f"run-invalid-outcome:{run.id}",
        )
        stats.runs_completed += 1
    if sync_experiments:
        try:
            from app.aiqe.services import triage_service

            from app.aiqe.models.triage import TriageExperiment

            for run_id in [item["run_id"] for item in stats.finalized_runs]:
                experiments = list(
                    db.scalars(
                        select(TriageExperiment).where(
                            TriageExperiment.verification_run_id == run_id
                        )
                    )
                )
                for experiment in experiments:
                    triage_service.sync_experiment_result(db, experiment.id)
                    stats.experiments_synced.append(experiment.id)
        except Exception as exc:  # 实验同步失败不得影响对账主流程
            stats.errors.append(f"{type(exc).__name__}: {exc}")
    db.flush()
    # V16-003 §11：过期 Secret Handle 清理（幂等；失败不影响对账结论）。
    try:
        from app.aiqe.services.secret_vault import purge_expired_handles

        stats.secrets_purged = purge_expired_handles(db)
    except Exception:
        stats.secrets_purged = 0
    # V16-006：Outbox relay（幂等发布；失败保留 pending 等下一轮）。
    try:
        from app.aiqe.services import outbox_service

        relayed = outbox_service.relay(db)
        stats.outbox_published = int(relayed.get("published") or 0)
        stats.outbox_failed = int(relayed.get("failed") or 0)
    except Exception:
        stats.outbox_published = 0
        stats.outbox_failed = 0
    return stats

_thread: threading.Thread | None = None
_stop = threading.Event()


def start_reconciler(poll_seconds: float | None = None) -> None:
    """AUD-006：后台对账线程（默认关闭，由 AIQE_RECONCILER_ENABLED 控制）。"""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    interval = float(poll_seconds or 30.0)
    _stop.clear()

    def loop() -> None:
        from app.core.db import SessionLocal

        while not _stop.wait(interval):
            db = SessionLocal()
            try:
                reconcile(db)
                db.commit()
            except Exception:  # 单次对账失败不得终止线程
                db.rollback()
            finally:
                db.close()

    _thread = threading.Thread(target=loop, name="aiqe-reconciler", daemon=True)
    _thread.start()


def stop_reconciler() -> None:
    global _thread
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=5)
        _thread = None
