"""M6 / TA-033：Reliability + Security Hardening 单测。"""
from __future__ import annotations

import uuid

import pytest

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import hardening_service
from app.aiqe.services.hardening_service import (
    HardeningError,
    audit_permission_denied,
    recover_after_worker_kill,
    run_idempotent_mutation,
)


def make_run(db_session, status="RUNNING", outcome=None):
    run = TestRun(
        project_id=1, run_key=f"run-{uuid.uuid4()}", status=status, outcome=outcome
    )
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            NodeRun(run_id=run.id, node_key="running", status="RUNNING"),
            NodeRun(run_id=run.id, node_key="pending", status="PENDING"),
            NodeRun(run_id=run.id, node_key="done", status="COMPLETED"),
        ]
    )
    db_session.flush()
    return run


def test_worker_kill_controlled_failure(db_session):
    run = make_run(db_session)
    result = recover_after_worker_kill(db_session, run.id)
    assert result["status"] == "COMPLETED"
    assert result["outcome"] == "INCOMPLETE"
    assert result["blocked_nodes"] == 2
    nodes = {node.node_key: node for node in run.node_runs}
    assert nodes["running"].status == "BLOCKED"
    assert nodes["pending"].status == "BLOCKED"
    assert nodes["done"].status == "COMPLETED"
    assert nodes["running"].error_class == "WORKER_LOST"


def test_recovery_is_idempotent(db_session):
    run = make_run(db_session)
    recover_after_worker_kill(db_session, run.id)
    again = recover_after_worker_kill(db_session, run.id)
    assert again["recovered"] is False
    assert again["blocked_nodes"] == 0


def test_terminal_run_untouched(db_session):
    run = make_run(db_session, status="COMPLETED", outcome="PASS")
    result = recover_after_worker_kill(db_session, run.id)
    assert result["recovered"] is False
    assert run.outcome == "PASS"


def test_unknown_run_rejected(db_session):
    with pytest.raises(HardeningError):
        recover_after_worker_kill(db_session, "missing")


def test_idempotent_mutation_executes_once(db_session):
    calls = []

    def mutation():
        calls.append(1)
        return {"charged": True}

    first, executed = run_idempotent_mutation(db_session, "charge-1", mutation)
    second, executed_again = run_idempotent_mutation(db_session, "charge-1", mutation)
    assert first == second == {"charged": True}
    assert executed is True and executed_again is False
    assert len(calls) == 1


def test_different_keys_execute_twice(db_session):
    calls = []
    run_idempotent_mutation(db_session, "seed-a", lambda: calls.append("a") or {"ok": 1})
    run_idempotent_mutation(db_session, "seed-b", lambda: calls.append("b") or {"ok": 2})
    assert calls == ["a", "b"]


def test_permission_denied_is_audited(db_session, monkeypatch):
    captured = []
    monkeypatch.setattr(
        hardening_service.audit_service,
        "write_audit",
        lambda *args, **kwargs: captured.append(kwargs),
    )
    monkeypatch.setattr(db_session, "commit", lambda: None)

    audit_permission_denied(
        db_session,
        user_id=7,
        username="tester",
        project_id=1,
        action="defect:update",
        target="defect:9",
    )
    assert captured and captured[0]["detail"] == "permission_denied"
    assert captured[0]["action"] == "defect:update"
