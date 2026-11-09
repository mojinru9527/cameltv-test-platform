"""M1 / TA-006：Event Collector + Outbox 单测（13 号 §4.11 / §18.6）。"""
from __future__ import annotations

import pytest

from app.aiqe.models.event import EventOutbox, RunEvent
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services.event_service import (
    InvalidEventPayload,
    RunNotFound,
    append_event,
    dispatch_outbox,
    list_events,
)


def _run(db, key="RUN-20261110-00001") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="RUNNING")
    db.add(run)
    db.flush()
    return run


def _payload(**extra):
    data = {"schema_version": "1.0", "message": "hello"}
    data.update(extra)
    return data


def test_1000_events_seq_contiguous(db_session):
    run = _run(db_session)
    for i in range(1000):
        append_event(
            db_session,
            run_id=run.id,
            event_type="node.started",
            payload=_payload(seq=i),
            producer="node",
            producer_event_id=f"e-{i}",
        )
    db_session.commit()

    seqs = [
        row.seq
        for row in db_session.query(RunEvent)
        .filter_by(run_id=run.id)
        .order_by(RunEvent.seq)
        .all()
    ]
    assert seqs == list(range(1, 1001))
    assert len(set(seqs)) == 1000
    assert db_session.query(EventOutbox).count() == 1000


def test_duplicate_producer_event_id_is_idempotent(db_session):
    run = _run(db_session)
    first, created1 = append_event(
        db_session,
        run_id=run.id,
        event_type="step.passed",
        payload=_payload(),
        producer="node",
        producer_event_id="same-id",
    )
    second, created2 = append_event(
        db_session,
        run_id=run.id,
        event_type="step.passed",
        payload=_payload(),
        producer="node",
        producer_event_id="same-id",
    )
    db_session.commit()
    assert created1 is True and created2 is False
    assert first.id == second.id
    assert db_session.query(RunEvent).count() == 1
    assert db_session.query(EventOutbox).count() == 1


def test_rollback_removes_event_and_outbox(db_session):
    run = _run(db_session)
    append_event(
        db_session,
        run_id=run.id,
        event_type="node.started",
        payload=_payload(),
        producer="system",
    )
    db_session.rollback()
    assert db_session.query(RunEvent).count() == 0
    assert db_session.query(EventOutbox).count() == 0


def test_projection_runs_in_same_transaction(db_session):
    run = _run(db_session)
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http", status="QUEUED")
    db_session.add(node)
    db_session.flush()

    def project(db, event):
        row = db.get(NodeRun, node.id)
        row.status = "RUNNING"

    append_event(
        db_session,
        run_id=run.id,
        event_type="node.started",
        payload=_payload(),
        producer="node",
        node_run_id=node.id,
        project=project,
    )
    db_session.commit()
    db_session.refresh(node)
    assert node.status == "RUNNING"


def test_projection_failure_rolls_back_event(db_session):
    run = _run(db_session)

    def project(db, event):
        raise RuntimeError("projection boom")

    with pytest.raises(RuntimeError):
        append_event(
            db_session,
            run_id=run.id,
            event_type="node.started",
            payload=_payload(),
            producer="node",
            project=project,
        )
    db_session.rollback()
    assert db_session.query(RunEvent).count() == 0
    assert db_session.query(EventOutbox).count() == 0


def test_payload_requires_schema_version(db_session):
    run = _run(db_session)
    with pytest.raises(InvalidEventPayload):
        append_event(
            db_session,
            run_id=run.id,
            event_type="x",
            payload={"message": "no version"},
            producer="system",
        )


def test_unknown_producer_rejected(db_session):
    run = _run(db_session)
    with pytest.raises(InvalidEventPayload):
        append_event(
            db_session,
            run_id=run.id,
            event_type="x",
            payload=_payload(),
            producer="hacker",
        )


def test_unknown_run_rejected(db_session):
    with pytest.raises(RunNotFound):
        append_event(
            db_session,
            run_id="no-such-run",
            event_type="x",
            payload=_payload(),
            producer="system",
        )


def test_dispatch_outbox_marks_once(db_session):
    run = _run(db_session)
    for i in range(3):
        append_event(
            db_session,
            run_id=run.id,
            event_type="node.step",
            payload=_payload(i=i),
            producer="node",
            producer_event_id=f"d-{i}",
        )
    db_session.commit()
    assert dispatch_outbox(db_session) == 3
    db_session.commit()
    assert dispatch_outbox(db_session) == 0
    assert (
        db_session.query(EventOutbox)
        .filter(EventOutbox.dispatched_at.isnot(None))
        .count()
        == 3
    )


def test_list_events_after_seq(db_session):
    run = _run(db_session)
    for i in range(5):
        append_event(
            db_session,
            run_id=run.id,
            event_type="e",
            payload=_payload(i=i),
            producer="system",
            producer_event_id=f"l-{i}",
        )
    db_session.commit()
    rows = list_events(db_session, run.id, after_seq=2, limit=10)
    assert [r.seq for r in rows] == [3, 4, 5]
