"""V3.9-R3 FINGER-001 — fingerprint/snapshot confidence persisted + gate requirement.

Verifies the environment confidence is actually persisted (EnvironmentFingerprint /
EnvironmentSnapshot) and that the Quality Gate's G9 (run env == target build) can
never PASS when the target Build fingerprint was only LOW-confidence observed — a
P0 release gate requires MEDIUM/HIGH (plan §57).
"""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import QualityGateResult
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous.schemas import FingerprintCaptureIn
from app.modules.aitde.environment import snapshot_service
from app.modules.aitde.environment.fingerprint import confidence_from_components
from app.modules.aitde.execution.models import EnvironmentSnapshot, ExecutionRun
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario as ScenarioModel,
    TestScenarioVersion as ScenarioVersionModel,
)
from app.modules.aitde.scope.models import ScopeItem


def _seed_gate_graph(db, *, build_confidence: str) -> tuple[int, int]:
    """Seed a minimal G9 graph: build fingerprint(+confidence) + a matching run."""
    db.add(Mission(id=7, project_id=1, mission_key="m", title="M", current_contract_version_id=100))
    db.add(ScopeItem(mission_id=7, scope_key="s1", decision="INCLUDE", review_status="APPROVED"))
    db.add(ScenarioModel(id=1, project_id=1, mission_id=7, scenario_key="s1"))
    db.add(
        ScenarioVersionModel(
            id=10, scenario_id=1, version_no=1, contract_version_id=100,
            risk_level="P0", title="Scenario",
        )
    )
    # Fingerprint of the target Build (confidence is the variable under test).
    from app.modules.aitde.continuous.models import EnvironmentFingerprint

    db.add(
        EnvironmentFingerprint(
            id=200, environment_id=1, fingerprint_hash="fp-target",
            source_type="AUTO", confidence=build_confidence,
        )
    )
    db.add(
        EnvironmentSnapshot(
            id=50, environment_id=1, mission_id=7,
            fingerprint_hash="fp-target", confidence="HIGH",
        )
    )
    db.add(
        ExecutionRun(
            id=900, project_id=1, mission_id=7, scenario_id=1, scenario_version_id=10,
            contract_version_id=100, environment_id=1, environment_snapshot_id=50,
            runtime_status="FINISHED", outcome="PASS", evidence_status="COMPLETE",
            trigger_type="MANUAL",
        )
    )
    # BuildObservation binds the campaign to the fingerprint.
    from app.modules.aitde.continuous.models import BuildObservation, CampaignScenario, ExecutionCampaign

    db.add(BuildObservation(id=300, mission_id=7, environment_id=1, fingerprint_id=200, status="NEW"))
    db.flush()
    db.add(
        ExecutionCampaign(
            id=400, project_id=1, mission_id=7, environment_id=1,
            campaign_type="FULL", build_observation_id=300, status="COMPLETED",
            created_by_type="AUTO",
        )
    )
    db.flush()
    db.add(
        CampaignScenario(
            id=500, campaign_id=400, scenario_id=1, scenario_version_id=10,
            required="REQUIRED", run_id=900,
        )
    )
    db.commit()
    return 400, 300


def test_confidence_from_components_levels():
    assert confidence_from_components({}) == "LOW"
    assert confidence_from_components({"service_versions": {"a": "1"}}) == "MEDIUM"
    assert confidence_from_components(
        {"service_versions": {"a": "1"}, "openapi_hash": "x", "db_schema_version": "y"}
    ) == "HIGH"


def test_capture_fingerprint_persists_confidence(db):
    fp = service.capture_fingerprint(
        db, 1,
        FingerprintCaptureIn(
            components={"service_versions": {"api": "1.0"}, "openapi_hash": "ab", "db_schema_version": "3"},
            build_label="build-1",
        ),
    )
    assert fp["confidence"] == "HIGH"
    # Re-capture with only a manual label -> LOW confidence is persisted.
    fp2 = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components={}, build_label="build-2")
    )
    assert fp2["confidence"] == "LOW"


def test_capture_snapshot_persists_confidence(db):
    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=7, project_id=1,
        data={"service_versions": {"a": "1"}, "openapi_hash": "x", "config_hash": "z"},
    )
    assert snap.confidence == "HIGH"


def test_gate_g9_fails_on_low_confidence_build(db):
    campaign_id, build_id = _seed_gate_graph(db, build_confidence="LOW")
    gate = service.evaluate_gate(db, 1, 7, campaign_id, build_id)
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    # Even with a matching snapshot, a LOW-confidence build cannot pass G9.
    assert checks["G9_RUN_ENV_MATCHES_BUILD"]["pass"] is False
    assert gate["result"] == QualityGateResult.FAIL.value


def test_gate_g9_passes_on_high_confidence_build(db):
    campaign_id, build_id = _seed_gate_graph(db, build_confidence="HIGH")
    gate = service.evaluate_gate(db, 1, 7, campaign_id, build_id)
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G9_RUN_ENV_MATCHES_BUILD"]["pass"] is True
