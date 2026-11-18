"""v1.4 FIX-006：Reconciler 状态收敛测试。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services.reconciler import reconcile
from app.models.execution_job import ExecutionJob


def _seed(db, *, job_status="running", lease_delta=-3600, node_status="RUNNING"):
    run = TestRun(
        project_id=1, run_key=f"RUN-REC-{job_status}-{node_status}", source_type="manual", status="RUNNING"
    )
    db.add(run)
    db.flush()
    node = NodeRun(
        run_id=run.id, node_key="n1", driver_key="http", status=node_status, attempt_count=1
    )
    db.add(node)
    db.flush()
    attempt = StepAttempt(
        node_run_id=node.id, step_key="n1", attempt_no=1, status="RUNNING"
    )
    db.add(attempt)
    job = ExecutionJob(
        project_id=1,
        kind="api",
        status=job_status,
        payload_json=f'{{"run_id":"{run.id}","node_run_id":"{node.id}"}}',
        claimed_at=datetime.now(UTC) - timedelta(hours=2),
        started_at=datetime.now(UTC) - timedelta(hours=2),
        heartbeat_at=datetime.now(UTC) - timedelta(hours=2),
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=lease_delta),
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    db.add(job)
    db.flush()
    node.execution_job_id = job.id
    db.commit()
    return run, node, job, attempt


def test_expired_lease_closes_node_and_run(db_session):
    run, node, job, attempt = _seed(db_session)
    stats = reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    assert stats["nodes_closed"] == 1
    node = db_session.get(NodeRun, node.id)
    assert node.status == "ERROR"
    assert node.error_class == "LEASE_EXPIRED"
    run = db_session.get(TestRun, run.id)
    assert run.status == "COMPLETED"
    assert run.outcome == "FAIL"
    job = db_session.get(ExecutionJob, job.id)
    assert job.status == "failed"
    assert job.error_message == "LEASE_EXPIRED"


def test_failed_job_closes_node(db_session):
    run, node, job, _ = _seed(db_session, job_status="failed", lease_delta=3600)
    job.error_message = "runner crashed"
    db_session.commit()
    reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert node.status == "FAILED"
    assert node.error_class == "JOB_FAILED"
    assert db_session.get(TestRun, run.id).outcome == "FAIL"


def test_stale_pending_job_blocks_node(db_session):
    run, node, job, _ = _seed(
        db_session, job_status="pending", lease_delta=3600, node_status="READY"
    )
    reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert node.status == "BLOCKED"
    assert node.error_class == "NODE_UNAVAILABLE"
    run = db_session.get(TestRun, run.id)
    assert run.status == "COMPLETED" and run.outcome == "INCOMPLETE"


def test_all_nodes_terminal_finalizes_run(db_session):
    run, node, job, attempt = _seed(db_session, job_status="success", lease_delta=3600)
    node.status = "PASSED"
    attempt.status = "PASSED"
    db_session.commit()
    reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert run.status == "COMPLETED" and run.outcome == "PASS"


def test_completed_without_outcome_is_error(db_session):
    run = TestRun(project_id=1, run_key="RUN-REC-BAD", source_type="manual", status="COMPLETED")
    db_session.add(run)
    db_session.commit()
    reconcile(db_session)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(TestRun, run.id).status == "ERROR"


def test_running_without_nodes_is_error(db_session):
    run = TestRun(project_id=1, run_key="RUN-REC-ORPHAN", source_type="manual", status="RUNNING")
    db_session.add(run)
    db_session.commit()
    reconcile(db_session)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(TestRun, run.id).status == "ERROR"
