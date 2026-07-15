"""Regression tests for caller-owned Agent queue writes and SQLite lock handling."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError


SQLITE_LOCK_MESSAGES = (
    "database is locked",
    "database table is locked",
    "database schema is locked",
)


def _locked_error(message: str = "database is locked") -> OperationalError:
    return OperationalError("INSERT", {}, Exception(message))


def test_enqueue_uses_caller_session_without_committing(db_session, monkeypatch):
    from app.services.knowledge import agent_queue

    commit = MagicMock()
    monkeypatch.setattr(db_session, "commit", commit)

    item = agent_queue.enqueue(
        db_session,
        project_id=1,
        agent_type="case_generation",
        operator_id=7,
    )

    assert item.id > 0
    assert item.status == "pending"
    assert item.operator_id == 7
    commit.assert_not_called()


def test_enqueue_retries_locked_flush_then_succeeds(db_session, monkeypatch):
    from app.services.knowledge import agent_queue

    original_flush = db_session.flush
    flush_calls = 0

    def flush_once_locked():
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 1:
            raise _locked_error()
        return original_flush()

    sleep = MagicMock()
    monkeypatch.setattr(db_session, "flush", flush_once_locked)
    monkeypatch.setattr(agent_queue.time, "sleep", sleep)

    item = agent_queue.enqueue(
        db_session,
        project_id=1,
        agent_type="case_generation",
    )

    assert flush_calls == 2
    assert item.id > 0
    assert item.status == "pending"
    sleep.assert_called_once_with(0.05)


@pytest.mark.parametrize("lock_message", SQLITE_LOCK_MESSAGES)
def test_enqueue_raises_controlled_busy_after_lock_retries(
    lock_message, db_session, monkeypatch,
):
    from app.services.knowledge import agent_queue

    flush = MagicMock(side_effect=_locked_error(lock_message))
    sleep = MagicMock()
    monkeypatch.setattr(db_session, "flush", flush)
    monkeypatch.setattr(agent_queue.time, "sleep", sleep)

    with pytest.raises(agent_queue.QueueWriteBusy, match="temporarily busy"):
        agent_queue.enqueue(
            db_session,
            project_id=1,
            agent_type="case_generation",
        )

    assert flush.call_count == 3
    assert sleep.call_count == 2


def test_enqueue_does_not_mask_non_lock_operational_error(db_session, monkeypatch):
    from app.services.knowledge import agent_queue

    error = OperationalError("INSERT", {}, Exception("disk I/O error"))
    monkeypatch.setattr(db_session, "flush", MagicMock(side_effect=error))

    with pytest.raises(OperationalError, match="disk I/O error"):
        agent_queue.enqueue(
            db_session,
            project_id=1,
            agent_type="case_generation",
        )


@pytest.mark.parametrize("lock_message", SQLITE_LOCK_MESSAGES)
def test_commit_queue_write_maps_sqlite_lock_to_controlled_busy(
    lock_message, db_session, monkeypatch,
):
    from app.services.knowledge import agent_queue

    rollback = MagicMock()
    monkeypatch.setattr(
        db_session,
        "commit",
        MagicMock(side_effect=_locked_error(lock_message)),
    )
    monkeypatch.setattr(db_session, "rollback", rollback)

    with pytest.raises(agent_queue.QueueWriteBusy, match="temporarily busy"):
        agent_queue.commit_queue_write(db_session)

    rollback.assert_called_once_with()


def test_commit_queue_write_does_not_mask_non_lock_error(db_session, monkeypatch):
    from app.services.knowledge import agent_queue

    error = OperationalError("COMMIT", {}, Exception("disk I/O error"))
    monkeypatch.setattr(db_session, "commit", MagicMock(side_effect=error))

    with pytest.raises(OperationalError, match="disk I/O error"):
        agent_queue.commit_queue_write(db_session)
