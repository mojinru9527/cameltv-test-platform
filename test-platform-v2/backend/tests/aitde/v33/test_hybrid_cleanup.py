"""V33-009 Hybrid coordinator (finally cleanup) tests."""
from __future__ import annotations

import json
from datetime import datetime

from app.modules.aitde.data import fixture_service, service
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.data.schemas import DataPlanGenerateRequest
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.hybrid.coordinator import HybridExecutionCoordinator
from app.modules.aitde.scenario.models import TestScenarioVersion as ScenarioVersion


def _make_ready(db, patched_db_driver):
    """Build a scenario version + DB_FIXTURE plan (approved) + provisioned fixture."""
    v = ScenarioVersion(
        scenario_id=1, version_no=1, contract_version_id=1, title="t",
        given_model_json=json.dumps({"user.status": "normal"}, ensure_ascii=False),
        expected_state_json="{}",
    )
    db.add(v)
    db.flush()
    src = DataSource(
        project_id=1, source_type="MYSQL", name="db", access_mode="READWRITE",
        config_json=json.dumps({"table_allowlist": ["user"]}, ensure_ascii=False), created_by=9,
    )
    db.add(src)
    db.flush()
    service.derive_data_requirements(db, v.id)
    plan = service.generate_data_plan(db, v.id, None, 1, DataPlanGenerateRequest())
    service.approve_data_plan(db, plan.id, 9)
    fixture = fixture_service.provision_fixture(db, plan, src, None, 1)
    db.flush()
    return v, fixture


def _run(db, scenario_version_id):
    run = ExecutionRun(
        project_id=1, mission_id=1, scenario_id=1, scenario_version_id=scenario_version_id,
        contract_version_id=1, environment_id=0, runtime_status="RUNNING",
        started_at=datetime.now(), created_by=9,
    )
    db.add(run)
    db.flush()
    return run


def test_hybrid_prepares_and_cleans_up(db, patched_db_driver):
    version, _ = _make_ready(db, patched_db_driver)
    run = _run(db, version.id)
    state = HybridExecutionCoordinator().run(db, run, project_id=1)
    assert state["data"]["prepared"] is True
    # cleanup ALWAYS ran after action/oracle and reached a real terminal state
    # (SUCCEEDED only when the compensation actually executed + verified).
    assert state.get("cleanup") and state["cleanup"]["status"] in (
        "SUCCEEDED", "FAILED", "PARTIAL",
    )


def test_hybrid_cleans_up_even_if_action_raises(db, patched_db_driver):
    version, _ = _make_ready(db, patched_db_driver)
    run = _run(db, version.id)

    def bad_action(_ctx):
        raise RuntimeError("browser action exploded")

    state = HybridExecutionCoordinator(action_runner=bad_action).run(db, run, project_id=1)
    # cleanup still ran in finally and reached a real terminal state.
    assert state.get("cleanup") and state["cleanup"]["status"] in (
        "SUCCEEDED", "FAILED", "PARTIAL",
    )
