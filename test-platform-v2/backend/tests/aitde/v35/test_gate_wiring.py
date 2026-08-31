"""AITDE V3.5 QualityGate G8/G9/G10 wiring tests.

These cover the code-pending §93 invariants:
  - Required Evidence 缺失不得 Gate PASS  (G8)
  - Run EnvironmentSnapshot == target Build  (G9)
  - 旧 ContractVersion Run 不算当前 Gate 通过  (G10)
And the §92 DoD "Acceptance 可解释每个 Gate" (every check carries label + detail).
"""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import QualityGateResult
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous.models import (
    BuildObservation,
    CampaignScenario,
    EnvironmentFingerprint,
    ExecutionCampaign,
)
from app.modules.aitde.execution.models import EnvironmentSnapshot, ExecutionRun
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    ScenarioOracleBinding,
    TestOracle,
    TestScenario as ScenarioModel,
    TestScenarioVersion as ScenarioVersionModel,
)
from app.modules.aitde.scope.models import ScopeItem


def _seed(
    db,
    *,
    evidence_status: str = "COMPLETE",
    run_contract_version_id: int = 100,
    snapshot_fingerprint_hash: str = "fp-target",
    build_fingerprint_hash: str = "fp-target",
    mission_current_contract_version_id: int | None = 100,
    outcome: str = "PASS",
    scope_items: bool = True,
    oracle_binding: bool = True,
    run_id: int | None = 900,
) -> tuple[int, int]:
    """Seed a full G1-G10 graph: mission + contract, scenario, run, build."""
    db.add(
        Mission(
            id=7, project_id=1, mission_key="m", title="M",
            current_contract_version_id=mission_current_contract_version_id,
        )
    )
    db.add(ScenarioModel(id=1, project_id=1, mission_id=7, scenario_key="s1"))
    if scope_items:
        db.add(
            ScopeItem(
                mission_id=7, scope_key="s1", decision="INCLUDE",
                review_status="APPROVED",
            )
        )
    db.add(
        ScenarioVersionModel(
            id=10, scenario_id=1, version_no=1, contract_version_id=100,
            risk_level="P0", title="Scenario",
        )
    )
    db.add(
        TestOracle(
            id=11, scenario_version_id=10, oracle_key="o1", oracle_type="API",
            expected_value_json='"OK"', required=True, review_status="APPROVED",
        )
    )
    if oracle_binding:
        db.add(
            ScenarioOracleBinding(
                scenario_adapter_id=1, scenario_version_id=10, oracle_id=11,
                binding_type="API_JSONPATH", source_step_key="s1",
                observation_selector_json='{"jsonpath":"$.status"}', status="ACTIVE",
            )
        )
    db.add(
        EnvironmentSnapshot(
            id=50, environment_id=1, mission_id=7,
            fingerprint_hash=snapshot_fingerprint_hash,
        )
    )
    if run_id is not None:
        db.add(
            ExecutionRun(
                id=run_id, project_id=1, mission_id=7, scenario_id=1,
                scenario_version_id=10, contract_version_id=run_contract_version_id,
                environment_id=1, environment_snapshot_id=50,
                runtime_status="FINISHED", outcome=outcome,
                evidence_status=evidence_status, trigger_type="MANUAL",
            )
        )
    db.add(
        EnvironmentFingerprint(
            id=200, environment_id=1, fingerprint_hash=build_fingerprint_hash,
            source_type="AUTO", confidence="HIGH",
        )
    )
    db.add(
        BuildObservation(
            id=300, mission_id=7, environment_id=1, fingerprint_id=200,
            status="NEW",
        )
    )
    db.flush()
    db.add(
        ExecutionCampaign(
            id=400, project_id=1, mission_id=7, environment_id=1,
            campaign_type="FULL", build_observation_id=300, status="RUNNING",
            created_by_type="AUTO",
        )
    )
    db.flush()
    db.add(
        CampaignScenario(
            id=500, campaign_id=400, scenario_id=1, scenario_version_id=10,
            required="REQUIRED", run_id=run_id,
        )
    )
    db.commit()
    return 400, 300


def _gate(db):
    return service.evaluate_gate(db, 1, 7, 400, 300)


def test_gate_all_green_passes(db):
    _seed(db)
    gate = _gate(db)
    assert gate["result"] == QualityGateResult.PASS.value
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G8_REQUIRED_EVIDENCE_COMPLETE"]["pass"] is True
    assert checks["G9_RUN_ENV_MATCHES_BUILD"]["pass"] is True
    assert checks["G10_RUN_CONTRACT_MATCHES_FROZEN"]["pass"] is True


def test_gate_g8_missing_evidence_fails(db):
    _seed(db, evidence_status="INCOMPLETE")
    gate = _gate(db)
    assert gate["result"] == QualityGateResult.FAIL.value
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G8_REQUIRED_EVIDENCE_COMPLETE"]["pass"] is False


def test_gate_g10_old_contract_version_fails(db):
    # Run bound to contract 99 while the Mission's current frozen contract is 100.
    _seed(db, run_contract_version_id=99)
    gate = _gate(db)
    assert gate["result"] == QualityGateResult.FAIL.value
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G10_RUN_CONTRACT_MATCHES_FROZEN"]["pass"] is False


def test_gate_g9_env_snapshot_mismatch_fails(db):
    # Run snapshot fingerprint differs from the target Build fingerprint.
    _seed(db, snapshot_fingerprint_hash="fp-old", build_fingerprint_hash="fp-target")
    gate = _gate(db)
    assert gate["result"] == QualityGateResult.FAIL.value
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G9_RUN_ENV_MATCHES_BUILD"]["pass"] is False


def test_gate_checks_explainable(db):
    _seed(db)
    gate = _gate(db)
    checks = json.loads(gate["checks_json"])
    assert len(checks) == 10
    assert all(isinstance(c["pass"], bool) for c in checks)
    # Every check must expose a human label + a detail summary (DoD §92).
    assert all(c["label"] for c in checks)
    assert all(c["detail"] for c in checks)


def test_gate_g1_needs_decided_scope_not_vacuous(db):
    # No scope items at all -> G1 must be False (never a bare "Scope Approved ✓").
    campaign_id, build_id = _seed(db, scope_items=False)
    gate = service.evaluate_gate(db, 1, 7, campaign_id, build_id)
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G1_SCOPE_APPROVED"]["pass"] is False


def test_gate_g3_g9_never_vacuous_pass(db):
    # A required scenario with no run (executed=0) must FAIL, and G9 must not
    # pass when env_checked == 0.
    campaign_id, build_id = _seed(db, run_id=None)
    gate = service.evaluate_gate(db, 1, 7, campaign_id, build_id)
    assert gate["result"] == QualityGateResult.FAIL.value
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G5_REQUIRED_SCENARIO_EXECUTED"]["pass"] is False
    assert checks["G9_RUN_ENV_MATCHES_BUILD"]["pass"] is False


def test_gate_g4_requires_oracle_binding_not_vacuous(db):
    # A required oracle with NO ACTIVE OracleBinding must be G4 False (real query,
    # never a hardcoded "oracle coverage ✓").
    campaign_id, build_id = _seed(db, oracle_binding=False)
    gate = service.evaluate_gate(db, 1, 7, campaign_id, build_id)
    checks = {c["gate"]: c for c in json.loads(gate["checks_json"])}
    assert checks["G4_ORACLE_COVERAGE_COMPLETE"]["pass"] is False
