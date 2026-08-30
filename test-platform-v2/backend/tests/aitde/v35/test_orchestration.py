"""AITDE V3.5 Continuous Acceptance orchestration tests (fire/webhook/build-diff).

Covers the §93 "待外部基础设施" wiring that drives the loop end-to-end:
  - fire_trigger: fingerprint → build → campaign (idempotent) → gate   (494/495)
  - build_diff: deterministic change summary between two fingerprints (500)
"""
from __future__ import annotations

from app.modules.aitde.common.enums import (
    ContinuousTriggerType,
    FingerprintSourceType,
)
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous.schemas import TriggerIn
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario as ScenarioModel,
    TestScenarioVersion as ScenarioVersionModel,
)


def _seed_mission_scenario(db) -> None:
    db.add(Mission(id=7, project_id=1, mission_key="m", title="M"))
    db.add(ScenarioModel(id=1, project_id=1, mission_id=7, scenario_key="s1"))
    db.add(
        ScenarioVersionModel(
            id=10, scenario_id=1, version_no=1, contract_version_id=100,
            risk_level="P0", title="Scenario",
        )
    )
    db.commit()


def _seed_trigger(db, *, config=None) -> int:
    trig = service.create_trigger(
        db,
        TriggerIn(
            project_id=1, mission_id=7, trigger_type=ContinuousTriggerType.FINGERPRINT,
            config=config or {"environment_id": 1, "mission_id": 7},
        ),
    )
    return trig["id"]


def test_fire_trigger_creates_campaign(db):
    _seed_mission_scenario(db)
    trigger_id = _seed_trigger(db)
    result = service.fire_trigger(
        db, 1, trigger_id,
        components={"service_versions": {"api": "1.0"}, "openapi_hash": "ab"},
    )
    assert result["duplicate_campaign"] is False
    assert result["campaign"]["build_observation_id"] == result["build_observation"]["id"]
    assert result["fingerprint"]["fingerprint_hash"]
    # Zero execution -> the gate is never PASS; it must not crash.
    assert result["gate"]["result"] in ("FAIL", "INCONCLUSIVE")


def test_fire_trigger_same_build_is_idempotent(db):
    _seed_mission_scenario(db)
    trigger_id = _seed_trigger(db)
    components = {"service_versions": {"api": "1.0"}, "openapi_hash": "ab"}
    r1 = service.fire_trigger(db, 1, trigger_id, components=components)
    r2 = service.fire_trigger(db, 1, trigger_id, components=components)
    # Same build (unchanged fingerprint) -> same observation + SAME campaign, no duplicate.
    assert r1["duplicate_campaign"] is False
    assert r2["duplicate_campaign"] is True
    assert r1["build_observation"]["id"] == r2["build_observation"]["id"]
    assert r1["campaign"]["id"] == r2["campaign"]["id"]
    assert r1["gate"]["id"] != r2["gate"]["id"]  # re-evaluated, still one campaign


def test_fire_trigger_new_build_creates_new_campaign(db):
    _seed_mission_scenario(db)
    trigger_id = _seed_trigger(db)
    r1 = service.fire_trigger(
        db, 1, trigger_id, components={"service_versions": {"api": "1.0"}, "openapi_hash": "a"}
    )
    r2 = service.fire_trigger(
        db, 1, trigger_id, components={"service_versions": {"api": "1.1"}, "openapi_hash": "b"}
    )
    assert r1["campaign"]["id"] != r2["campaign"]["id"]
    assert r2["duplicate_campaign"] is False
    assert r2["build_observation"]["previous_fingerprint_id"] == r1["fingerprint"]["id"]


def test_build_diff_detects_changes(db):
    fp_a = service.capture_fingerprint(
        db, 1,
        service.FingerprintCaptureIn(
            components={"service_versions": {"api": "1.0"}, "openapi_hash": "x"},
            source_type=FingerprintSourceType.AUTO,
        ),
    )
    fp_b = service.capture_fingerprint(
        db, 1,
        service.FingerprintCaptureIn(
            components={"service_versions": {"api": "1.1"}, "openapi_hash": "y"},
            source_type=FingerprintSourceType.AUTO,
        ),
    )
    diff = service.build_diff(db, fp_a["id"], fp_b["id"])
    assert diff["changed"] is True
    assert "service_versions" in diff["changed_areas"]
    assert "openapi_hash" in diff["changed_areas"]
    assert diff["service_changes"]["api"] == {"from": "1.0", "to": "1.1"}


def test_build_diff_initial_is_changed(db):
    fp = service.capture_fingerprint(
        db, 1,
        service.FingerprintCaptureIn(components={"service_versions": {"api": "1.0"}}),
    )
    diff = service.build_diff(db, None, fp["id"])
    assert diff["changed"] is True
    assert "initial_build" in diff["changed_areas"]
