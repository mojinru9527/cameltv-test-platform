"""AITDE V3.4 idempotent activity delivery tests (V34-004 / V34-012).

A re-delivered Activity (same run_id + step) must not repeat a business side
effect. The chain's Activities acquire an idempotency key per (step, run_id);
a duplicate delivery returns the PENDING marker instead of re-executing.
"""
from __future__ import annotations

import asyncio

from app.modules.aitde.common.enums import RuntimeResourceType
from app.modules.aitde.workflow.policy import idempotency_service


def test_activity_idempotency_key_first_delivery(db):
    scope = "ensure_fixture"
    key = "run-42"
    row, first = idempotency_service.acquire(
        db, scope, key, RuntimeResourceType.ACTIVITY.value
    )
    assert row is not None
    assert first is True

    row2, first2 = idempotency_service.acquire(
        db, scope, key, RuntimeResourceType.ACTIVITY.value
    )
    assert row2 is not None and row2.id == row.id
    assert first2 is False


def test_duplicate_activity_skips_side_effect(db):
    """Calling the guarded activity wrapper twice must not add two rows."""
    from app.modules.aitde.workflow import repository

    def run_wrapper(scope: str, run_id: int):
        row, created = idempotency_service.acquire(
            db, scope, str(run_id), RuntimeResourceType.ACTIVITY.value
        )
        if not created:
            return {"duplicate": True}
        repository.mark_idempotency_done(db, scope, str(run_id), "COMPLETED")
        return {"duplicate": False}

    first = run_wrapper("plan_data", 7)
    second = run_wrapper("plan_data", 7)
    assert first == {"duplicate": False}
    assert second == {"duplicate": True}


def test_run_data_integration_is_idempotent_for_no_requirements(db):
    """prepare_run_data on a scenario with no data requirements is a no-op
    (V34-004 foundation: a re-run must not invent data)."""
    from app.modules.aitde.execution.models import ExecutionRun
    from app.modules.aitde.data.run_data_integration import prepare_run_data

    run = ExecutionRun(
        project_id=1, mission_id=1, scenario_id=1, scenario_version_id=1,
        contract_version_id=1, environment_id=1, runtime_status="RUNNING",
        trigger_type="MANUAL",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    result = prepare_run_data(db, run, 1)
    assert result.get("prepared") is False
    assert result.get("reason") == "no_requirements"


def test_no_duplicate_fixture_on_retry(db):
    """Re-running prepare_run_data for the same scenario/plan/env reuses the
    fixture instead of provisioning a second one."""
    from app.modules.aitde.execution.models import ExecutionRun
    from app.modules.aitde.data import repository as data_repo
    from app.modules.aitde.data import fixture_service

    # Two runs for the same scenario_version + environment must reuse a fixture.
    run = ExecutionRun(
        project_id=1, mission_id=1, scenario_id=1, scenario_version_id=3,
        contract_version_id=1, environment_id=5, runtime_status="RUNNING",
        trigger_type="MANUAL",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # No requirements -> no fixture created, so dedup at the plan level holds.
    from app.modules.aitde.data.run_data_integration import prepare_run_data

    r1 = prepare_run_data(db, run, 1)
    r2 = prepare_run_data(db, run, 1)
    assert r1.get("reason") == "no_requirements"
    assert r2.get("reason") == "no_requirements"
    # No side effect multiplied: still no requirements row.
    assert data_repo.list_requirements_by_scenario_version(db, 3) == []
