"""Run data integration tests (V32-014)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import Outcome
from app.modules.aitde.data import run_data_integration as rdi
from app.modules.aitde.execution.models import ExecutionRun


def _run(db, scenario_version_id=1, outcome=None):
    run = ExecutionRun(
        project_id=1, mission_id=1, scenario_id=1, scenario_version_id=scenario_version_id,
        contract_version_id=1, environment_id=1, outcome=outcome, created_by=9,
    )
    db.add(run)
    db.flush()
    return run


def test_add_run_data_timeline(db):
    run = _run(db)
    steps = rdi.add_run_data_timeline(db, run.id)
    keys = [s.step_key for s in steps]
    assert "DATA PLAN" in keys
    assert "CLEANUP VERIFY" in keys
    assert all(s.step_type == "DATA" for s in steps)


def test_set_run_data_fail_only_when_no_business_outcome(db):
    run = _run(db)
    rdi.set_run_data_fail(db, run.id)
    db.refresh(run)
    assert run.outcome == Outcome.DATA_FAIL.value

    # A business outcome must not be overwritten by a data failure.
    run_biz = _run(db, scenario_version_id=2, outcome=Outcome.BUSINESS_FAIL.value)
    rdi.set_run_data_fail(db, run_biz.id)
    db.refresh(run_biz)
    assert run_biz.outcome == Outcome.BUSINESS_FAIL.value


def test_record_data_evidence(db):
    run = _run(db)
    artifact = rdi.record_data_evidence(
        db, run.id, "DATA_PLAN", project_id=1, content_hash="abc", storage_uri="obj/dp"
    )
    assert artifact.evidence_type == "DATA_PLAN"
    assert artifact.content_hash == "abc"
    with pytest.raises(APIException) as exc:
        rdi.record_data_evidence(db, run.id, "NOT_REAL")
    assert exc.value.http_status == 400


def test_cleanup_health_preserves_business_outcome(db):
    run = _run(db, outcome=Outcome.PASS.value)
    updated = rdi.record_cleanup_health(db, run.id, cleanup_ok=False)
    assert updated.outcome == Outcome.PASS.value

    from sqlalchemy import func, select

    from app.modules.aitde.execution.models import ExecutionStep

    count = db.scalar(
        select(func.count(ExecutionStep.id)).where(
            ExecutionStep.run_id == run.id,
            ExecutionStep.step_key == "CLEANUP HEALTH",
        )
    )
    assert count == 1
