"""Run data integration wiring tests (V32-014 auto-on-run)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.modules.aitde.common.enums import Outcome, RunStatus
from app.modules.aitde.data.models import DataFixture
from app.modules.aitde.data.run_data_integration import prepare_run_data
from app.modules.aitde.execution import service as exec_service
from app.modules.aitde.execution.models import (
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
)


def _run(db, scenario_version_id, outcome=None, runtime_status=RunStatus.RUNNING.value):
    run = ExecutionRun(
        project_id=1, mission_id=1, scenario_id=1, scenario_version_id=scenario_version_id,
        contract_version_id=1, environment_id=0, outcome=outcome,
        runtime_status=runtime_status, started_at=datetime.now(), created_by=9,
    )
    db.add(run)
    db.flush()
    return run


def test_prepare_run_data_happy(db, ready_fixture):
    version = ready_fixture["version"]
    run = _run(db, version.id)
    res = prepare_run_data(db, run, project_id=1)
    assert res["prepared"] is True
    assert res["fixture_id"]

    # DATA timeline steps appended to the run
    steps = db.scalars(
        select(ExecutionStep).where(
            ExecutionStep.run_id == run.id, ExecutionStep.step_type == "DATA"
        )
    ).all()
    assert len(steps) >= 1
    assert any(s.step_key == "CLEANUP" for s in steps)

    # data evidence recorded
    artifacts = db.scalars(
        select(EvidenceArtifact).where(EvidenceArtifact.run_id == run.id)
    ).all()
    assert any(a.evidence_type == "DATA_PLAN" for a in artifacts)
    assert any(a.evidence_type == "FIXTURE_MANIFEST" for a in artifacts)

    # fixture is linked to the run
    linked = db.scalar(select(DataFixture).where(DataFixture.run_id == run.id))
    assert linked is not None
    assert linked.id == res["fixture_id"]


def test_prepare_run_data_no_requirements_is_noop(db):
    # A run whose scenario has no data requirements -> no data prep, no timeline.
    run = _run(db, scenario_version_id=99999)
    res = prepare_run_data(db, run, project_id=1)
    assert res["prepared"] is False
    assert res["reason"] == "no_requirements"


def test_prepare_run_data_reuses_fixture(db, ready_fixture):
    """Idempotency: a second prepare for the same plan reuses (not duplicates)."""
    version = ready_fixture["version"]
    run = _run(db, version.id)
    first = prepare_run_data(db, run, project_id=1)
    # exercise the reuse path with a different run
    run2 = _run(db, version.id)
    second = prepare_run_data(db, run2, project_id=1)
    assert first["prepared"] is True
    assert second["prepared"] is True
    # the same fixture is reused for the same (scenario_version, data_plan)
    assert second["fixture_id"] == first["fixture_id"]


def test_finish_run_preserves_data_fail(db):
    run = _run(db, scenario_version_id=1, outcome=Outcome.DATA_FAIL.value)
    updated = exec_service.finish_run(db, run.id, project_id=1, outcome_str=Outcome.BUSINESS_FAIL.value)
    db.refresh(updated)
    assert updated.runtime_status == RunStatus.FINISHED.value
    # DATA_FAIL is authoritative over the business outcome.
    assert updated.outcome == Outcome.DATA_FAIL.value


def test_mark_running_prepares_data(db, ready_fixture):
    """mark_running (run start) automatically provisions data for the run."""
    version = ready_fixture["version"]
    run = _run(db, version.id, runtime_status=RunStatus.QUEUED.value)
    started = exec_service.mark_running(db, run.id, project_id=1)
    db.refresh(started)
    assert started.runtime_status == RunStatus.RUNNING.value
    steps = db.scalars(
        select(ExecutionStep).where(
            ExecutionStep.run_id == run.id, ExecutionStep.step_type == "DATA"
        )
    ).all()
    assert len(steps) >= 1
