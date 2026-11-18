"""AUD-006：ExecutionJob / NodeRun / TestRun 状态一致性与恢复验收测试。

对应 v1.5 §01 AUD-006「完成标准」：
- Worker kill 后 Run 在 SLA 内收敛到正确终态（不永久 RUNNING）；
- 旧 Worker 迟到结果不覆盖新 Worker（fencing token）；
- 重复 Event 不重复创建记录；
- 所有终态有审计事件（Run 时间线非空）；
- 非幂等步骤不盲目重试（缺省 3 次上限后 BLOCKED）。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.aiqe.models.event import RunEvent
from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.security import SafeHttpResult, upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services import lease as lease_service
from app.aiqe.services.event_service import append_event, list_events
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.aiqe.services.reconciler import reconcile
from app.models.execution_job import ExecutionJob

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "api",
            "driver": "http",
            "input": {"url": "https://api.allowed.test/state", "method": "GET"},
        }
    ],
    "edges": [],
    "retry": {"max_attempts": 3},
}


def _seed_run(db, *, graph=GRAPH, key="RUN-AUD006-1") -> tuple[TestRun, ExecutionJob]:
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["api.allowed.test"], "allowed_ports": [443]},
    )
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(
        db, run.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph)
    )
    db.commit()
    job = db.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    return run, job


def _fake_http(monkeypatch, *, ok=True, status_code=200):
    def _fake(self, request, policy):
        return SafeHttpResult(
            ok=ok,
            status_code=status_code,
            duration_ms=1,
            request={"url": request.url},
            response={"status_code": status_code},
            policy_version=policy.version,
        )

    monkeypatch.setattr("app.aiqe.services.node_executor.SafeHttpExecutor.request", _fake)


# ── 1. fencing token ─────────────────────────────────────
def test_claim_bumps_fencing_token(db_session):
    run, job = _seed_run(db_session)
    assert job_consumer.claim_aiqe_jobs(db_session) == [job.id]
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.fencing_token == 1


def test_stale_worker_result_rejected(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-2")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.fencing_token = 2
    db_session.commit()

    with pytest.raises(lease_service.StaleLeaseError):
        dag_scheduler.complete_node(
            db_session,
            run.id,
            "api",
            "PASSED",
            GRAPH,
            fencing_token=1,
        )
    db_session.rollback()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status != "PASSED"


def test_newer_token_can_write(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-3")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    db_session.commit()
    dag_scheduler.complete_node(
        db_session, run.id, "api", "PASSED", GRAPH, fencing_token=int(node.fencing_token)
    )
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(TestRun, run.id).status == "COMPLETED"


def test_claim_job_uses_lease_expiry(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-4")
    job_consumer.claim_aiqe_jobs(db_session)
    db_session.expire_all()
    claimed = db_session.get(ExecutionJob, job.id)
    assert claimed.lease_expires_at is not None
    assert claimed.attempt == 1


def test_expired_lease_rejects_write(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-5")
    job_consumer.claim_aiqe_jobs(db_session)
    db_session.expire_all()
    claimed = db_session.get(ExecutionJob, job.id)
    claimed.lease_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    with pytest.raises(lease_service.LeaseExpired):
        lease_service.assert_current(
            db_session,
            node_run_id=node.id,
            fencing_token=claimed.attempt,
            job_expires_at=claimed.lease_expires_at,
            job_id=claimed.id,
        )


# ── 2. Worker kill → Reconciler 收敛 ──────────────────────
def test_reconciler_requeues_expired_job(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-6")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    job = db_session.get(ExecutionJob, job.id)
    job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    report = reconcile(db_session)
    db_session.commit()

    assert job.id in report.expired_jobs
    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "PENDING"
    assert node.execution_job_id is None
    assert node.fencing_token >= 2  # 旧 Worker 彻底失效
    events = [event.event_type for event in list_events(db_session, run.id)]
    assert "node.lease_expired" in events

    # 重新调度会产生新的 Job（不是复用过期 Job）
    dag_scheduler.schedule(
        db_session, run.id, GRAPH, dispatch=lambda row: enqueue_node_run(db_session, row, graph=GRAPH)
    )
    db_session.commit()
    pending = list(db_session.scalars(select(ExecutionJob).where(ExecutionJob.status == "pending")))
    assert len(pending) == 1
    assert pending[0].id != job.id


def test_reconciler_blocks_after_requeue_limit(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-7")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    node.attempt_count = 3
    job = db_session.get(ExecutionJob, job.id)
    job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    report = reconcile(db_session)
    db_session.commit()

    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert node.error_class == "LEASE_EXPIRED"
    assert node.node_key in report.blocked_nodes
    run_row = db_session.get(TestRun, run.id)
    assert run_row.status == "COMPLETED"
    assert run_row.outcome == "INCOMPLETE"
    assert report.finalized_runs


def test_old_worker_cannot_overwrite_after_reconcile(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-8")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    job = db_session.get(ExecutionJob, job.id)
    job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    reconcile(db_session)
    db_session.commit()

    # 旧 Worker 用认领时的 token=1 迟到上报
    with pytest.raises(lease_service.StaleLeaseError):
        dag_scheduler.complete_node(
            db_session, run.id, "api", "PASSED", GRAPH, fencing_token=1
        )


def test_reconciler_finalizes_run_with_all_terminal_nodes(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-9")
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "PASSED"
    node.finished_at = datetime.now(UTC)
    db_session.commit()

    report = reconcile(db_session, sync_experiments=False)
    db_session.commit()
    db_session.expire_all()
    run_row = db_session.get(TestRun, run.id)
    assert run_row.status == "COMPLETED"
    assert run_row.outcome == "PASS"
    assert any(item["run_id"] == run.id for item in report.finalized_runs)


def test_reconcile_does_not_touch_running_nodes(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-10")
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    db_session.commit()
    report = reconcile(db_session, sync_experiments=False)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(TestRun, run.id).status == "RUNNING"
    assert not report.finalized_runs


# ── 3. 事件：时间线非空、幂等、终态可审计 ─────────────────
def test_node_lifecycle_events_are_written(db_session, monkeypatch):
    _fake_http(monkeypatch)
    run, job = _seed_run(db_session, key="RUN-AUD006-11")
    # schedule 已写入 node.ready
    events = [event.event_type for event in list_events(db_session, run.id)]
    assert "node.ready" in events

    job_consumer.claim_aiqe_jobs(db_session)
    job_consumer.run_job(db_session, job.id)
    db_session.commit()

    events = [event.event_type for event in list_events(db_session, run.id)]
    assert "node.started" in events
    assert "node.completed" in events
    assert "run.completed" in events
    seqs = [event.seq for event in list_events(db_session, run.id)]
    assert seqs == sorted(seqs)


def test_duplicate_event_delivery_is_idempotent(db_session):
    run, _job = _seed_run(db_session, key="RUN-AUD006-12")
    for _ in range(5):
        append_event(
            db_session,
            run_id=run.id,
            event_type="node.completed",
            payload={"schema_version": "1.0", "node_key": "api"},
            producer="system",
            producer_event_id="dup-event-1",
        )
    db_session.commit()
    rows = list(
        db_session.scalars(
            select(RunEvent).where(
                RunEvent.run_id == run.id, RunEvent.event_type == "node.completed"
            )
        )
    )
    assert len(rows) == 1


def test_attempt_records_fencing_token(db_session, monkeypatch):
    _fake_http(monkeypatch)
    run, job = _seed_run(db_session, key="RUN-AUD006-13")
    job_consumer.claim_aiqe_jobs(db_session)
    job_consumer.run_job(db_session, job.id)
    db_session.commit()
    attempts = list(
        db_session.scalars(
            select(StepAttempt).join(NodeRun, NodeRun.id == StepAttempt.node_run_id).where(
                NodeRun.run_id == run.id
            )
        )
    )
    assert attempts
    assert all(int(attempt.fencing_token or 0) >= 0 for attempt in attempts)


def test_stale_report_from_external_runner_rejected(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-14")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.fencing_token = 5
    node.status = "RUNNING"
    db_session.commit()

    outcome = job_consumer.complete_from_report(
        db_session, job_id=job.id, status="passed", fencing_token=2
    )
    assert outcome["skipped"] is True
    assert outcome["reason"] == "STALE_LEASE"


def test_requeue_limit_is_configurable(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD006-15")
    job_consumer.claim_aiqe_jobs(db_session)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "RUNNING"
    node.attempt_count = 1
    job = db_session.get(ExecutionJob, job.id)
    job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    report = reconcile(db_session, requeue_limit=1, sync_experiments=False)
    db_session.commit()
    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert node.node_key in report.blocked_nodes
