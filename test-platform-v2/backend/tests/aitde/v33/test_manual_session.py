"""V33-008 Manual Assist session tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.manual import service
from app.modules.aitde.common.enums import ManualStepStatus


def test_create_and_steps_persist_refresh_recoverable(db):
    s = service.create_session(db, run_id=1, scenario_version_id=10, tester_id=9)
    st1 = service.add_step(db, s.id, "step-1")
    st2 = service.add_step(db, s.id, "step-2")
    assert st1.sequence == 1
    assert st2.sequence == 2
    assert st1.status == ManualStepStatus.PENDING.value

    done = service.complete_step(db, st1.id, ManualStepStatus.DONE.value, "ok", evidence_refs=[11, 12])
    assert done.status == ManualStepStatus.DONE.value
    assert done.tester_note == "ok"
    assert done.completed_at is not None

    # "刷新可恢复": re-list reflects the same durable state
    steps = service.list_steps(db, s.id)
    assert len(steps) == 2
    assert steps[0].status == ManualStepStatus.DONE.value


def test_illegal_step_status_rejected(db):
    s = service.create_session(db, run_id=1, scenario_version_id=10, tester_id=9)
    st = service.add_step(db, s.id, "step-x")
    with pytest.raises(APIException) as exc:
        service.complete_step(db, st.id, "WHATEVER")
    assert exc.value.http_status == 400


def test_finish_session(db):
    s = service.create_session(db, run_id=1, scenario_version_id=10, tester_id=9)
    finished = service.finish_session(db, s.id)
    assert finished.status == "FINISHED"
    assert finished.finished_at is not None
