"""M1 / TA-005：Run 事实源 ORM 约束与关联单测。"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.models.execution_job import ExecutionJob


def _run(db, key="RUN-20261110-00001") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="DRAFT")
    db.add(run)
    db.flush()
    return run


def test_run_node_step_assertion_chain(db_session):
    run = _run(db_session)
    node = NodeRun(run_id=run.id, node_key="create_match", driver_key="http")
    db_session.add(node)
    db_session.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="request", attempt_no=1)
    db_session.add(attempt)
    db_session.flush()
    assertion = RunAssertionResult(
        step_attempt_id=attempt.id,
        assertion_key="http_ok",
        assertion_type="value",
        status="PASS",
        expected_json={"status": 200},
        actual_json={"status": 200},
    )
    db_session.add(assertion)
    db_session.commit()

    db_session.refresh(run)
    assert [n.node_key for n in run.node_runs] == ["create_match"]
    assert run.node_runs[0].step_attempts[0].assertion_results[0].assertion_key == "http_ok"


def test_run_key_unique_per_project(db_session):
    _run(db_session)
    db_session.add(TestRun(project_id=1, run_key="RUN-20261110-00001"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_node_key_unique_per_run(db_session):
    run = _run(db_session)
    db_session.add_all(
        [
            NodeRun(run_id=run.id, node_key="same", driver_key="http"),
            NodeRun(run_id=run.id, node_key="same", driver_key="http"),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_attempt_no_unique_per_step(db_session):
    run = _run(db_session)
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http")
    db_session.add(node)
    db_session.flush()
    db_session.add_all(
        [
            StepAttempt(node_run_id=node.id, step_key="s1", attempt_no=1),
            StepAttempt(node_run_id=node.id, step_key="s1", attempt_no=1),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_node_run_links_execution_job(db_session):
    run = _run(db_session)
    job = ExecutionJob(project_id=1, kind="ui", status="pending")
    db_session.add(job)
    db_session.flush()
    node = NodeRun(
        run_id=run.id, node_key="ui", driver_key="playwright", execution_job_id=job.id
    )
    db_session.add(node)
    db_session.commit()
    db_session.refresh(node)
    assert node.execution_job_id == job.id
    assert job.id is not None


def test_cascade_delete_run(db_session):
    run = _run(db_session)
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http")
    db_session.add(node)
    db_session.commit()
    db_session.delete(run)
    db_session.commit()
    assert db_session.query(NodeRun).count() == 0
