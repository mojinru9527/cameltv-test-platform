"""V3.9-R3 CONT-001 — Campaign 真执行 (real run instantiation + gate gating).

Verifies the Continuous campaign actually RUNS: freezing the selection creates a
real ExecutionRun per scenario and binds it to the CampaignScenario, the campaign
only becomes terminal (COMPLETED/PARTIAL) when every run is FINISHED, and the
Quality Gate is never final (INCONCLUSIVE / CAMPAIGN_NOT_FINISHED) while the
campaign is still in progress.
"""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import QualityGateResult
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous.models import ExecutionCampaign
from app.modules.aitde.continuous.schemas import CampaignCreateIn, TriggerIn
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario as ScenarioModel,
    TestScenarioVersion as ScenarioVersionModel,
)
from app.modules.aitde.scope.models import ScopeItem


def _seed_mission_scenario(db) -> tuple[int, int]:
    db.add(
        Mission(id=7, project_id=1, mission_key="m", title="M", current_contract_version_id=100)
    )
    db.add(ScopeItem(mission_id=7, scope_key="s1", decision="INCLUDE", review_status="APPROVED"))
    db.add(ScenarioModel(id=1, project_id=1, mission_id=7, scenario_key="s1"))
    db.add(
        ScenarioVersionModel(
            id=10, scenario_id=1, version_no=1, contract_version_id=100,
            risk_level="P0", title="Scenario",
        )
    )
    db.commit()
    return 7, 10


def _create_campaign(db, mission_id, scenario_version_id=10) -> int:
    camp = service.create_campaign(
        db,
        CampaignCreateIn(
            project_id=1,
            mission_id=mission_id,
            name="c",
            environment_id=1,
            build_observation_id=300,
            scenarios=[
                {
                    "scenario_id": 1,
                    "scenario_version_id": scenario_version_id,
                    "required": "REQUIRED",
                    "selection_reason": {"planner": "v1"},
                }
            ],
        ),
    )
    return camp["id"]


def test_start_campaign_execution_creates_real_runs_and_binds(db):
    mission_id, svid = _seed_mission_scenario(db)
    campaign_id = _create_campaign(db, mission_id, svid)
    state = service.start_campaign_execution(db, 1, campaign_id)

    assert state["status"] == "RUNNING"
    scenario = state["scenarios"][0]
    assert scenario["run_id"] is not None
    run = db.get(ExecutionRun, scenario["run_id"])
    assert run is not None
    assert run.scenario_version_id == svid
    assert run.contract_version_id == 100
    assert run.environment_id == 1


def test_start_campaign_execution_is_idempotent(db):
    mission_id, svid = _seed_mission_scenario(db)
    campaign_id = _create_campaign(db, mission_id, svid)
    s1 = service.start_campaign_execution(db, 1, campaign_id)
    run_id = s1["scenarios"][0]["run_id"]
    s2 = service.start_campaign_execution(db, 1, campaign_id)
    # Same campaign, same bound run — never duplicated.
    assert s2["scenarios"][0]["run_id"] == run_id
    assert db.query(ExecutionRun).count() == 1


def test_finalize_waits_for_terminal_then_completes(db):
    mission_id, svid = _seed_mission_scenario(db)
    campaign_id = _create_campaign(db, mission_id, svid)
    state = service.start_campaign_execution(db, 1, campaign_id)
    run_id = state["scenarios"][0]["run_id"]

    # Not terminal yet -> campaign stays RUNNING (no fabricated completion).
    assert service.finalize_campaign(db, campaign_id, 1)["status"] == "RUNNING"

    # Drive the run to FINISHED and re-finalize.
    run = db.get(ExecutionRun, run_id)
    run.runtime_status = "FINISHED"
    run.outcome = "PASS"
    run.evidence_status = "COMPLETE"
    db.commit()
    assert service.finalize_campaign(db, campaign_id, 1)["status"] == "COMPLETED"
    row = db.get(ExecutionCampaign, campaign_id)
    assert row.status == "COMPLETED"


def test_finalize_marks_partial_when_required_run_fails(db):
    mission_id, svid = _seed_mission_scenario(db)
    campaign_id = _create_campaign(db, mission_id, svid)
    state = service.start_campaign_execution(db, 1, campaign_id)
    run = db.get(ExecutionRun, state["scenarios"][0]["run_id"])
    run.runtime_status = "FINISHED"
    run.outcome = "BUSINESS_FAIL"
    run.evidence_status = "INCOMPLETE"
    db.commit()
    assert service.finalize_campaign(db, campaign_id, 1)["status"] == "PARTIAL"


def test_gate_is_not_final_while_campaign_running(db):
    mission_id, svid = _seed_mission_scenario(db)
    campaign_id = _create_campaign(db, mission_id, svid)
    state = service.start_campaign_execution(db, 1, campaign_id)
    gate = service.evaluate_gate(
        db, 1, mission_id, campaign_id, 300, campaign_status=state["status"]
    )
    assert gate["result"] == QualityGateResult.INCONCLUSIVE.value
    checks = {c["gate"] for c in json.loads(gate["checks_json"])}
    assert "CAMPAIGN_NOT_FINISHED" in checks


def test_fire_trigger_creates_runs_and_gate_not_finished(db):
    mission_id, svid = _seed_mission_scenario(db)
    trigger_id = service.create_trigger(
        db,
        TriggerIn(
            project_id=1,
            mission_id=mission_id,
            trigger_type="FINGERPRINT",
            config={"environment_id": 1, "mission_id": mission_id},
        ),
    )["id"]
    result = service.fire_trigger(
        db, 1, trigger_id,
        components={"service_versions": {"api": "1.0"}, "openapi_hash": "ab"},
    )
    # CONT-001: a real ExecutionRun was created and bound per campaign scenario.
    assert result["campaign"]["status"] == "RUNNING"
    assert result["campaign"]["scenarios"][0]["run_id"] is not None
    # Gate is not final while the campaign is still running.
    assert result["gate"]["result"] == QualityGateResult.INCONCLUSIVE.value
    assert "CAMPAIGN_NOT_FINISHED" in json.dumps(result["gate"]["checks_json"])
