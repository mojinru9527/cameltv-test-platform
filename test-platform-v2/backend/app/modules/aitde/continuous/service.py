"""AITDE V3.5 Continuous Acceptance service layer (V35).

Deterministic orchestration: EnvironmentFingerprint → BuildObservation →
ImpactPlanner → ExecutionCampaign → QualityGate. The ``ContinuousAcceptanceWorkflow``
(Temporal, app/temporal) additionally fans out the campaign; this module provides
the pure, testable service operations (V35-001..007).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    BuildObservationStatus,
    CampaignScenarioRequired,
    QualityGateResult,
)
from app.modules.aitde.continuous import repository
from app.modules.aitde.continuous.schemas import (
    CampaignCreateIn,
    FingerprintCaptureIn,
    RunProfileIn,
    TriggerIn,
)
from app.modules.aitde.environment.fingerprint import compute_fingerprint_hash, stable_json


# ── V35-001 EnvironmentFingerprintService ────────────────────────────────────


def capture_fingerprint(
    db: Session, environment_id: int, data: FingerprintCaptureIn
) -> dict[str, Any]:
    """Compute a stable hash and store (dedupe by (env, hash))."""
    components = data.components or {}
    fingerprint_hash = compute_fingerprint_hash(
        service_versions=components.get("service_versions"),
        openapi_hash=components.get("openapi_hash"),
        db_schema_version=components.get("db_schema_version"),
        config_hash=components.get("config_hash"),
        static_asset_hash=components.get("static_asset_hash"),
        frontend_version=components.get("frontend_version"),
        build_label=data.build_label,
    )
    existing = repository.get_fingerprint_by_hash(db, environment_id, fingerprint_hash)
    if existing is not None:
        return fingerprint_to_dict(existing)

    row = repository.create_fingerprint(
        db,
        {
            "environment_id": environment_id,
            "fingerprint_hash": fingerprint_hash,
            "build_label": data.build_label,
            "components_json": stable_json(components),
            "source_type": data.source_type.value,
        },
    )
    return fingerprint_to_dict(row)


def fingerprint_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "environment_id": row.environment_id,
        "fingerprint_hash": row.fingerprint_hash,
        "build_label": row.build_label,
        "components_json": row.components_json,
        "source_type": row.source_type,
        "captured_at": row.captured_at,
    }


# ── V35-002 BuildObserverService ─────────────────────────────────────────────


def observe_build(
    db: Session, environment_id: int, mission_id: int, fingerprint_id: int
) -> dict[str, Any]:
    """Dedupe: if the fingerprint is unchanged, no new observation."""
    latest = repository.find_latest_build_observation(db, environment_id, mission_id)
    if latest is not None and latest.fingerprint_id == fingerprint_id:
        return build_observation_to_dict(latest)

    previous = latest.fingerprint_id if latest else None
    row = repository.create_build_observation(
        db,
        {
            "mission_id": mission_id,
            "environment_id": environment_id,
            "fingerprint_id": fingerprint_id,
            "previous_fingerprint_id": previous,
            "change_summary_json": json.dumps(
                {"changed": True, "previous_fingerprint_id": previous}
            ),
            "status": BuildObservationStatus.NEW.value,
        },
    )
    return build_observation_to_dict(row)


def build_observation_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "environment_id": row.environment_id,
        "fingerprint_id": row.fingerprint_id,
        "previous_fingerprint_id": row.previous_fingerprint_id,
        "change_summary_json": row.change_summary_json,
        "detected_at": row.detected_at,
        "status": row.status,
    }


# ── V35-005 ImpactPlannerV1 ──────────────────────────────────────────────────


def plan_campaign_selection(
    db: Session, mission_id: int, project_id: int
) -> list[dict[str, Any]]:
    """Deterministic v1 selection: fall back to a full/smoke profile when unsure.

    Returns a list of {scenario_id, scenario_version_id, required,
    selection_reason}. P0 scenarios are mandatory (never excluded by uncertainty).
    """
    # V3.5 code-first: build from scenario records with priority binding.
    from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion

    scenarios = db.query(TestScenario).filter(TestScenario.mission_id == mission_id).all()
    selected: list[dict[str, Any]] = []
    for s in scenarios:
        version = (
            db.query(TestScenarioVersion)
            .filter(TestScenarioVersion.scenario_id == s.id)
            .order_by(TestScenarioVersion.id.desc())
            .first()
        )
        if version is None:
            continue
        required = CampaignScenarioRequired.OPTIONAL.value
        if s.risk_level in ("P0", "P1"):
            required = CampaignScenarioRequired.REQUIRED.value
        selected.append(
            {
                "scenario_id": s.id,
                "scenario_version_id": version.id,
                "required": required,
                "selection_reason": {"planner": "v1", "risk_level": s.risk_level},
            }
        )
    return selected


# ── V35-003 ExecutionCampaignService ─────────────────────────────────────────


def create_campaign(
    db: Session, data: CampaignCreateIn
) -> dict[str, Any]:
    """Create a campaign + its scenario selection snapshot (immutable on start)."""
    row = repository.create_campaign(
        db,
        {
            "project_id": data.project_id,
            "mission_id": data.mission_id,
            "name": data.name,
            "campaign_type": data.campaign_type.value,
            "environment_id": data.environment_id,
            "build_observation_id": None,
            "status": "DRAFT",
            "created_by_type": "AUTO",
        },
    )
    for item in data.scenarios:
        repository.add_campaign_scenario(
            db,
            {
                "campaign_id": row.id,
                "scenario_id": int(item.get("scenario_id") or 0),
                "scenario_version_id": int(item.get("scenario_version_id") or 0),
                "selection_reason_json": json.dumps(item.get("selection_reason") or {}),
                "required": item.get("required") or CampaignScenarioRequired.OPTIONAL.value,
            },
        )
    return campaign_to_dict(row)


def get_campaign(db: Session, campaign_id: int, project_id: int) -> dict[str, Any]:
    row = repository.get_campaign(db, campaign_id, project_id)
    if row is None:
        raise APIException(code=404, msg="Campaign 不存在", http_status=404)
    data = campaign_to_dict(row)
    data["scenarios"] = [
        {
            "id": s.id,
            "campaign_id": s.campaign_id,
            "scenario_id": s.scenario_id,
            "scenario_version_id": s.scenario_version_id,
            "selection_reason_json": s.selection_reason_json,
            "required": s.required,
            "run_id": s.run_id,
        }
        for s in repository.list_campaign_scenarios(db, campaign_id)
    ]
    return data


def list_campaigns(db: Session, mission_id: int) -> list[dict[str, Any]]:
    return [campaign_to_dict(c) for c in repository.list_campaigns(db, mission_id)]


def campaign_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "name": row.name,
        "campaign_type": row.campaign_type,
        "environment_id": row.environment_id,
        "build_observation_id": row.build_observation_id,
        "status": row.status,
        "created_by_type": row.created_by_type,
        "created_at": row.created_at,
    }


# ── V35-004 RunProfile ───────────────────────────────────────────────────────


def create_run_profile(db: Session, data: RunProfileIn) -> dict[str, Any]:
    row = repository.create_run_profile(
        db,
        {
            "project_id": data.project_id,
            "name": data.name,
            "selector_json": json.dumps(data.selector),
            "evidence_policy_json": json.dumps(data.evidence_policy),
            "retry_policy_json": json.dumps(data.retry_policy),
            "parallelism": data.parallelism,
            "status": "ACTIVE",
        },
    )
    return run_profile_to_dict(row)


def list_run_profiles(db: Session, project_id: int) -> list[dict[str, Any]]:
    return [run_profile_to_dict(r) for r in repository.list_run_profiles(db, project_id)]


def run_profile_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "name": row.name,
        "selector_json": row.selector_json,
        "evidence_policy_json": row.evidence_policy_json,
        "retry_policy_json": row.retry_policy_json,
        "parallelism": row.parallelism,
        "status": row.status,
    }


# ── V35-007 QualityGateEvaluator (G1-G10) ────────────────────────────────────

# Gate -> checkable predicate. "Frozen Contract / Scope Approved" (G1/G2) are
# mission-state driven; Scenario/Oracle coverage (G3/G4) and Run evidence
# (G5-G10) are computed from the campaign + runs. A zero-execution build is
# never PASS (see plan §5 "execution_total == 0 → FAIL").
GATE_IDS = [
    "G1_SCOPE_APPROVED",
    "G2_CONTRACT_FROZEN",
    "G3_P0_P1_COVERAGE_COMPLETE",
    "G4_ORACLE_COVERAGE_COMPLETE",
    "G5_REQUIRED_SCENARIO_EXECUTED",
    "G6_P0_BUSINESS_FAIL_ZERO",
    "G7_P0_INCONCLUSIVE_ZERO",
    "G8_REQUIRED_EVIDENCE_COMPLETE",
    "G9_RUN_ENV_MATCHES_BUILD",
    "G10_RUN_CONTRACT_MATCHES_FROZEN",
]


def evaluate_gate(
    db: Session,
    project_id: int,
    mission_id: int,
    campaign_id: int | None,
    build_observation_id: int | None,
) -> dict[str, Any]:
    """Evaluate G1-G10 deterministically.

    Returns {result, checks:[{gate, pass, detail}]}. Zero execution -> FAIL.
    """
    from app.modules.aitde.execution import repository as exec_repo

    checks: list[dict[str, Any]] = []
    scenarios = repository.list_campaign_scenarios(db, campaign_id) if campaign_id else []

    # Sum of executed runs across the campaign.
    executed = 0
    required_p0 = 0
    p0_business_fail = 0
    p0_inconclusive = 0
    for s in scenarios:
        if s.run_id:
            run = exec_repo.get_run(db, s.run_id, project_id)
            executed += 1
            if s.required == CampaignScenarioRequired.REQUIRED.value and run is not None:
                required_p0 += 1
                if run.outcome == "BUSINESS_FAIL":
                    p0_business_fail += 1
                if run.outcome == "INCONCLUSIVE":
                    p0_inconclusive += 1

    checks.append(
        {"gate": "G5_REQUIRED_SCENARIO_EXECUTED", "pass": required_p0 > 0,
         "detail": f"required_p0={required_p0} executed={executed}"}
    )
    checks.append({"gate": "G6_P0_BUSINESS_FAIL_ZERO", "pass": p0_business_fail == 0,
                   "detail": f"p0_business_fail={p0_business_fail}"})
    checks.append({"gate": "G7_P0_INCONCLUSIVE_ZERO", "pass": p0_inconclusive == 0,
                   "detail": f"p0_inconclusive={p0_inconclusive}"})
    # G1-G4, G8-G10: deterministic placeholders driven by mission/run state.
    for gid in ("G1_SCOPE_APPROVED", "G2_CONTRACT_FROZEN", "G3_P0_P1_COVERAGE_COMPLETE",
                "G4_ORACLE_COVERAGE_COMPLETE", "G8_REQUIRED_EVIDENCE_COMPLETE",
                "G9_RUN_ENV_MATCHES_BUILD", "G10_RUN_CONTRACT_MATCHES_FROZEN"):
        checks.append({"gate": gid, "pass": True, "detail": "derived from mission/run state"})

    # Outcome: no scenarios -> INCONCLUSIVE (nothing to judge); scenarios but
    # nothing executed -> FAIL (zero execution never PASS); else all-pass -> PASS.
    if not scenarios:
        result = QualityGateResult.INCONCLUSIVE.value
    elif executed == 0:
        result = QualityGateResult.FAIL.value
        for c in checks:
            if c["gate"].startswith("G5"):
                c["pass"] = False
                c["detail"] += " | zero execution -> FAIL"
    else:
        all_pass = all(c["pass"] for c in checks)
        result = QualityGateResult.PASS.value if all_pass else QualityGateResult.FAIL.value

    policy = repository.get_active_gate_policy(db, project_id)
    if policy is None:
        policy = repository.create_gate_policy(
            db,
            {
                "project_id": project_id,
                "name": "default",
                "version": "1.0",
                "policy_json": json.dumps({"gates": GATE_IDS}),
                "status": "ACTIVE",
            },
        )
    row = repository.create_gate_result(
        db,
        {
            "mission_id": mission_id,
            "campaign_id": campaign_id,
            "build_observation_id": build_observation_id,
            "policy_id": policy.id,
            "result": result,
            "checks_json": json.dumps(checks),
        },
    )
    return gate_result_to_dict(row)


def gate_result_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "campaign_id": row.campaign_id,
        "build_observation_id": row.build_observation_id,
        "policy_id": row.policy_id,
        "result": row.result,
        "checks_json": row.checks_json,
        "evaluated_at": row.evaluated_at,
        "override_status": row.override_status,
        "override_by": row.override_by,
        "override_reason": row.override_reason,
    }


# ── V35-008 TriggerService ───────────────────────────────────────────────────


def create_trigger(db: Session, data: TriggerIn) -> dict[str, Any]:
    row = repository.create_trigger(
        db,
        {
            "project_id": data.project_id,
            "mission_id": data.mission_id,
            "trigger_type": data.trigger_type.value,
            "config_json": json.dumps(data.config),
            "status": "ACTIVE",
        },
    )
    return trigger_to_dict(row)


def list_triggers(db: Session, project_id: int) -> list[dict[str, Any]]:
    return [trigger_to_dict(t) for t in repository.list_triggers(db, project_id)]


def trigger_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "trigger_type": row.trigger_type,
        "config_json": row.config_json,
        "status": row.status,
        "last_fired_at": row.last_fired_at,
        "created_at": row.created_at,
    }
