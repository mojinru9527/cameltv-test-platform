"""v1.4 FIX-006：Job / NodeRun / TestRun 状态对账（reconciler）。

解决"Job FAILED 但 NodeRun/TestRun 永远 RUNNING"与过期租约悬挂：
- 节点 READY/RUNNING 但 Job 丢失/失败/取消/租约过期 → 收敛为 ERROR/BLOCKED/FAILED；
- 所有节点终态但 Run 仍 RUNNING → 按事实收口 COMPLETED（PASS/FAIL/INCOMPLETE）；
- Run 没有任何节点且超时 → ERROR；
- COMPLETED 无 outcome → ERROR（违反状态机）。
所有收敛写 RunEvent，幂等（producer_event_id）。
"""
from __future__ import annotations

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
    if run.status != "RUNNING" or not nodes:
        return
    if any(node.status not in NODE_TERMINAL for node in nodes):
        return
    statuses = {node.node_key: node.status for node in nodes}
    if any(status in NODE_FAILED for status in statuses.values()):
        apply_transition(run, "COMPLETED", outcome="FAIL")
    elif any(status == "BLOCKED" for status in statuses.values()):
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


def reconcile(
    db: Session,
    *,
    stale_seconds: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """对账一批 RUNNING Run；返回统计。调用方负责 commit。"""
    stale = max(30, int(stale_seconds or 900))
    cutoff = _now() - timedelta(seconds=stale)
    runs = list(
        db.scalars(
            select(TestRun)
            .where(TestRun.status == "RUNNING")
            .order_by(TestRun.created_at)
            .limit(max(1, int(limit)))
        )
    )
    stats = {
        "runs_scanned": len(runs),
        "nodes_closed": 0,
        "jobs_failed": 0,
        "runs_completed": 0,
    }
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
            stats["runs_completed"] += 1
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
                stats["nodes_closed"] += 1
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
                stats["nodes_closed"] += 1
                continue
            if job.status == "running" and expired:
                job.status = "failed"
                job.error_message = "LEASE_EXPIRED"
                job.finished_at = _now()
                _close_node(db, node, "ERROR", "LEASE_EXPIRED", "Runner 租约过期")
                _event(
                    db,
                    run.id,
                    "node.reconciled",
                    {
                        "node_key": node.node_key,
                        "status": "ERROR",
                        "job_id": job.id,
                        "reason": "LEASE_EXPIRED",
                    },
                    key=f"node-reconciled:{node.id}:{job.id}:LEASE_EXPIRED",
                )
                stats["nodes_closed"] += 1
                stats["jobs_failed"] += 1
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
                    stats["nodes_closed"] += 1
        before = run.status
        _finalize_run(db, run, nodes)
        if before == "RUNNING" and run.status == "COMPLETED":
            stats["runs_completed"] += 1

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
        stats["runs_completed"] += 1
    db.flush()
    return stats
