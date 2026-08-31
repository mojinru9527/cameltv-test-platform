"""AITDE V3.5 Continuous Acceptance service layer (V35).

Deterministic orchestration: EnvironmentFingerprint → BuildObservation →
ImpactPlanner → ExecutionCampaign → QualityGate. The ``ContinuousAcceptanceWorkflow``
(Temporal, app/temporal) additionally fans out the campaign; this module provides
the pure, testable service operations (V35-001..007).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    BuildObservationStatus,
    CampaignScenarioRequired,
    CampaignType,
    EvidenceStatus,
    FingerprintSourceType,
    QualityGateResult,
)
from app.modules.aitde.continuous import repository
from app.modules.aitde.continuous.schemas import (
    CampaignCreateIn,
    FingerprintCaptureIn,
    RunProfileIn,
    TriggerIn,
)
from app.modules.aitde.environment.fingerprint import (
    compute_fingerprint_hash,
    confidence_from_components,
    stable_json,
)


# ── V35-001 EnvironmentFingerprintService ────────────────────────────────────


def capture_fingerprint(
    db: Session, environment_id: int, data: FingerprintCaptureIn
) -> dict[str, Any]:
    """Compute a stable hash and store (dedupe by (env, hash)).

    V3.9-R3 (FINGER-001): the fingerprint's confidence (how much was actually
    observed vs manually declared) is persisted so a P0 gate can require
    MEDIUM/HIGH before a Release Gate.
    """
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
            "confidence": confidence_from_components(components),
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
        "confidence": row.confidence,
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
        risk_level = version.risk_level or ""
        required = CampaignScenarioRequired.OPTIONAL.value
        if risk_level in ("P0", "P1"):
            required = CampaignScenarioRequired.REQUIRED.value
        selected.append(
            {
                "scenario_id": s.id,
                "scenario_version_id": version.id,
                "required": required,
                "selection_reason": {"planner": "v1", "risk_level": risk_level},
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
            "build_observation_id": data.build_observation_id,
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

# V3.9-R3 (CONT-001): the Quality Gate is final only when the Campaign reached a
# terminal state. Otherwise the gate is INCONCLUSIVE with reason CAMPAIGN_NOT_FINISHED.
CAMPAIGN_FINISHED = ("COMPLETED", "PARTIAL")
CAMPAIGN_NOT_FINISHED = "CAMPAIGN_NOT_FINISHED"

# Checks that must stay deterministic (never satisfied vacuously) — used by the
# Acceptance Dashboard to explain each gate (plan §5 / §92 DoD).
GATE_LABELS = {
    "G1_SCOPE_APPROVED": "范围已批准",
    "G2_CONTRACT_FROZEN": "契约已冻结",
    "G3_P0_P1_COVERAGE_COMPLETE": "P0/P1 场景覆盖完整",
    "G4_ORACLE_COVERAGE_COMPLETE": "必备 Oracle 覆盖完整",
    "G5_REQUIRED_SCENARIO_EXECUTED": "必备场景已为当前 Build 执行",
    "G6_P0_BUSINESS_FAIL_ZERO": "P0 业务失败为零",
    "G7_P0_INCONCLUSIVE_ZERO": "P0 无法判定为零",
    "G8_REQUIRED_EVIDENCE_COMPLETE": "必备证据完整",
    "G9_RUN_ENV_MATCHES_BUILD": "运行环境快照 == 目标 Build",
    "G10_RUN_CONTRACT_MATCHES_FROZEN": "运行契约版本 == 当前冻结契约",
}


def _mission_current_contract_version_id(db: Session, mission_id: int) -> int | None:
    """The Mission's current (frozen) contract version id, or ``None``."""
    from app.modules.aitde.mission.models import Mission

    mission = db.scalar(select(Mission).where(Mission.id == mission_id).limit(1))
    if mission is None:
        return None
    return getattr(mission, "current_contract_version_id", None)


def _build_target_fingerprint(
    db: Session, build_observation_id: int | None, mission_id: int
) -> tuple[str | None, str | None]:
    """Fingerprint hash + confidence of the target Build, or ``(None, None)``.

    Returns ``(fingerprint_hash, confidence)`` so the gate can require a
    MEDIUM/HIGH confidence for a P0 release (FINGER-001).
    """
    if not build_observation_id:
        return None, None
    from app.modules.aitde.continuous.models import EnvironmentFingerprint

    observation = repository.get_build_observation(db, build_observation_id, mission_id)
    if observation is None:
        return None, None
    fingerprint = db.scalar(
        select(EnvironmentFingerprint)
        .where(EnvironmentFingerprint.id == observation.fingerprint_id)
        .limit(1)
    )
    if fingerprint is None:
        return None, None
    return fingerprint.fingerprint_hash, fingerprint.confidence


def evaluate_gate(
    db: Session,
    project_id: int,
    mission_id: int,
    campaign_id: int | None,
    build_observation_id: int | None,
    campaign_status: str | None = None,
) -> dict[str, Any]:
    """Evaluate G1-G10 deterministically.

    Returns {result, checks:[{gate, label, pass, detail}]}. Zero execution -> FAIL.

    When ``campaign_status`` is supplied and is not a terminal campaign state
    (COMPLETED/PARTIAL), the gate is INCONCLUSIVE with reason CAMPAIGN_NOT_FINISHED
    (plan §51) — a Quality Gate is never final on an in-progress campaign.

    G8/G9/G10 are wired to run evidence, the run's environment snapshot and the
    run's contract version so that missing evidence, an old contract-version run
    or a mismatched environment snapshot can never silently PASS a gate
    (plan §5 / §93 invariants).
    """
    from app.modules.aitde.execution import repository as exec_repo

    checks: list[dict[str, Any]] = []
    scenarios = repository.list_campaign_scenarios(db, campaign_id) if campaign_id else []

    # Deterministic inputs derived from mission/build state.
    current_contract_version_id = _mission_current_contract_version_id(db, mission_id)
    contract_frozen = current_contract_version_id is not None
    target_fingerprint_hash, target_confidence = _build_target_fingerprint(
        db, build_observation_id, mission_id
    )

    # Aggregate per run across the campaign selection snapshot.
    executed = 0
    required_total = 0
    required_executed = 0
    required_with_version = 0
    p0_business_fail = 0
    p0_inconclusive = 0
    evidence_complete = 0
    contract_match = 0
    env_checked = 0
    env_match = 0
    for s in scenarios:
        is_required = s.required == CampaignScenarioRequired.REQUIRED.value
        if is_required:
            required_total += 1
            if s.scenario_version_id:
                required_with_version += 1
        if s.run_id is None:
            continue
        run = exec_repo.get_run(db, s.run_id, project_id)
        if run is None:
            continue
        executed += 1
        if is_required:
            required_executed += 1
            if run.outcome == "BUSINESS_FAIL":
                p0_business_fail += 1
            if run.outcome == "INCONCLUSIVE":
                p0_inconclusive += 1
        # G8 — evidence completeness.
        if run.evidence_status == EvidenceStatus.COMPLETE.value:
            evidence_complete += 1
        # G10 — run bound to the current frozen contract version.
        if current_contract_version_id is not None and run.contract_version_id == current_contract_version_id:
            contract_match += 1
        # G9 — run's environment snapshot matches the target Build fingerprint,
        # AND the target Build was observed with MEDIUM/HIGH confidence (FINGER-001:
        # a LOW-confidence build can never satisfy a P0 release gate).
        if target_fingerprint_hash is not None:
            env_checked += 1
            snapshot = (
                exec_repo.get_snapshot(db, run.environment_snapshot_id, project_id)
                if run.environment_snapshot_id
                else None
            )
            confidence_ok = target_confidence in ("MEDIUM", "HIGH")
            if (
                confidence_ok
                and snapshot is not None
                and snapshot.fingerprint_hash == target_fingerprint_hash
            ):
                env_match += 1

    # V3.9-R3 (CONT-002): G1/G3/G4 are real queries, never hardcoded True,
    # and G3/G9 are never vacuous-pass on a zero count.
    from app.modules.aitde.common.enums import ReviewStatus, ScopeDecision
    from app.modules.aitde.scenario.models import ScenarioOracleBinding, TestOracle
    from app.modules.aitde.scope.repository import list_items as list_scope_items

    # G1 — scope items all decided (no PROPOSED) and nothing left in review.
    scope_items = list_scope_items(db, mission_id)
    pending_scope = sum(
        1 for si in scope_items if si.review_status == ReviewStatus.PROPOSED.value
    )
    scope_decided = all(
        si.decision in (ScopeDecision.INCLUDE.value, ScopeDecision.EXCLUDE.value)
        for si in scope_items
    )
    g1_pass = bool(scope_items) and pending_scope == 0 and scope_decided
    g1_detail = f"scope_items={len(scope_items)} pending={pending_scope}"

    # G3 — required scenarios must exist AND all carry a scenario version.
    g3_pass = required_total > 0 and required_with_version == required_total

    # G4 — every required scenario has >=1 APPROVED required oracle AND every
    # required oracle has an ACTIVE OracleBinding.
    g4_missing: list[str] = []
    for s in scenarios:
        if s.required != CampaignScenarioRequired.REQUIRED.value:
            continue
        if not s.scenario_version_id:
            g4_missing.append(f"scenario {s.scenario_id} lacks version")
            continue
        oracles = db.scalars(
            select(TestOracle).where(
                TestOracle.scenario_version_id == s.scenario_version_id,
                TestOracle.required.is_(True),
            )
        ).all()
        if not oracles:
            g4_missing.append(f"scenario {s.scenario_id} has no required oracle")
            continue
        for oracle in oracles:
            if oracle.review_status != ReviewStatus.APPROVED.value:
                g4_missing.append(f"oracle {oracle.id} not approved")
                continue
            binding = db.scalar(
                select(ScenarioOracleBinding)
                .where(
                    ScenarioOracleBinding.scenario_version_id == s.scenario_version_id,
                    ScenarioOracleBinding.oracle_id == oracle.id,
                    ScenarioOracleBinding.status == "ACTIVE",
                )
                .limit(1)
            )
            if binding is None:
                g4_missing.append(f"oracle {oracle.id} has no binding")
    g4_pass = not g4_missing
    g4_detail = (
        "all required oracles approved + bound"
        if g4_pass
        else "; ".join(g4_missing[:3])
    )

    def check(gid: str, passed: bool, detail: str) -> dict[str, Any]:
        return {
            "gate": gid,
            "label": GATE_LABELS.get(gid, gid),
            "pass": bool(passed),
            "detail": detail,
        }

    checks.append(check("G1_SCOPE_APPROVED", g1_pass, g1_detail))
    checks.append(
        check(
            "G2_CONTRACT_FROZEN",
            contract_frozen,
            f"current_contract_version_id={current_contract_version_id}",
        )
    )
    checks.append(
        check(
            "G3_P0_P1_COVERAGE_COMPLETE",
            g3_pass,
            f"required_with_version={required_with_version}/{required_total}",
        )
    )
    checks.append(check("G4_ORACLE_COVERAGE_COMPLETE", g4_pass, g4_detail))
    checks.append(
        check(
            "G5_REQUIRED_SCENARIO_EXECUTED",
            required_executed > 0,
            f"required_executed={required_executed}/{required_total} executed={executed}",
        )
    )
    checks.append(
        check(
            "G6_P0_BUSINESS_FAIL_ZERO",
            p0_business_fail == 0,
            f"p0_business_fail={p0_business_fail}",
        )
    )
    checks.append(
        check(
            "G7_P0_INCONCLUSIVE_ZERO",
            p0_inconclusive == 0,
            f"p0_inconclusive={p0_inconclusive}",
        )
    )
    checks.append(
        check(
            "G8_REQUIRED_EVIDENCE_COMPLETE",
            executed > 0 and evidence_complete == executed,
            f"evidence_complete={evidence_complete}/{executed}",
        )
    )
    checks.append(
        check(
            "G9_RUN_ENV_MATCHES_BUILD",
            env_checked > 0 and env_match == env_checked,
            f"env_match={env_match}/{env_checked} target={target_fingerprint_hash or 'none'} conf={target_confidence or 'none'}",
        )
    )
    checks.append(
        check(
            "G10_RUN_CONTRACT_MATCHES_FROZEN",
            contract_frozen and contract_match == executed,
            f"contract_match={contract_match}/{executed} frozen={current_contract_version_id}",
        )
    )

    # Outcome: no scenarios -> INCONCLUSIVE (nothing to judge); scenarios but
    # nothing executed -> FAIL (zero execution never PASS); else all-pass -> PASS.
    # V3.9-R3 (CONT-001): an unfinished campaign is never given a final Gate.
    if campaign_status is not None and campaign_status not in CAMPAIGN_FINISHED:
        result = QualityGateResult.INCONCLUSIVE.value
        checks.append(
            {
                "gate": "CAMPAIGN_NOT_FINISHED",
                "label": "Campaign 未完成",
                "pass": False,
                "detail": f"campaign_status={campaign_status}",
            }
        )
    elif not scenarios:
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


def _json_dict(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


# ── V35-003 campaign execution (V3.9-R3 CONT-001) ────────────────────────────
# The Continuous campaign must actually RUN, not just declare a snapshot. These
# functions freeze the selection, create a real ExecutionRun per scenario and bind
# it to the CampaignScenario, then transition the Campaign only when its runs are
# terminal (COMPLETED / PARTIAL). The Quality Gate is final only at those states.


def _get_run(db: Session, run_id: int, project_id: int) -> Any:
    from app.modules.aitde.execution import repository as exec_repo

    return exec_repo.get_run(db, run_id, project_id)


def _create_run_for_campaign(
    db: Session, project_id: int, campaign: Any, item: Any
) -> Any:
    """Create a physical ExecutionRun for one campaign scenario (real run start)."""
    from app.modules.aitde.execution.models import ExecutionRun
    from app.modules.aitde.scenario.models import TestScenarioVersion

    version = db.get(TestScenarioVersion, item.scenario_version_id)
    contract_version_id = version.contract_version_id if version else 0
    run = ExecutionRun(
        project_id=project_id,
        mission_id=campaign.mission_id,
        scenario_id=item.scenario_id,
        scenario_version_id=item.scenario_version_id,
        contract_version_id=contract_version_id,
        environment_id=campaign.environment_id,
        runtime_status="SCHEDULED",
        trigger_type="AUTO",
        created_by=0,
    )
    db.add(run)
    db.flush()
    return run


def start_campaign_execution(
    db: Session,
    project_id: int,
    campaign_id: int,
    run_launcher: Callable[[Session, Any], None] | None = None,
) -> dict[str, Any]:
    """Freeze the selection and create a real ExecutionRun per campaign scenario.

    The campaign transitions DRAFT → RUNNING and every scenario is bound to a
    physical ExecutionRun (its ``run_id``) so ``evaluate_gate`` judges real runs,
    never a zero-execution build. ``run_launcher`` (optional) is invoked per run to
    actually start the ScenarioExecutionWorkflow (the Temporal gateway in
    production; an injected synchronizer in tests). Idempotent: a RUNNING /
    terminal campaign is never re-instantiated.
    """
    row = repository.get_campaign(db, campaign_id, project_id)
    if row is None:
        raise APIException(code=404, msg="Campaign 不存在", http_status=404)
    if row.status != "DRAFT":
        # Already started / finished; attempt to finalize and return as-is.
        return _finalize_campaign(db, row, project_id)

    scenarios = repository.list_campaign_scenarios(db, campaign_id)
    if not scenarios:
        row.status = "FAILED"
        db.commit()
        db.refresh(row)
        return get_campaign(db, campaign_id, project_id)

    row.status = "RUNNING"
    for item in scenarios:
        if item.run_id is not None:
            continue
        run = _create_run_for_campaign(db, project_id, row, item)
        item.run_id = run.id
        if run_launcher is not None:
            run_launcher(db, run)
    db.commit()
    db.refresh(row)
    return _finalize_campaign(db, row, project_id)


def finalize_campaign(db: Session, campaign_id: int, project_id: int) -> dict[str, Any]:
    """Transition RUNNING → COMPLETED / PARTIAL once every run is terminal.

    Every campaign scenario must be bound to a FINISHED run before the campaign
    may be considered terminal. A finished campaign is the ONLY state in which the
    Quality Gate is evaluated as final (plan §51).
    """
    row = repository.get_campaign(db, campaign_id, project_id)
    if row is None:
        raise APIException(code=404, msg="Campaign 不存在", http_status=404)
    return _finalize_campaign(db, row, project_id)


def _finalize_campaign(db: Session, row: Any, project_id: int) -> dict[str, Any]:
    if row.status != "RUNNING":
        return get_campaign(db, row.id, project_id)

    scenarios = repository.list_campaign_scenarios(db, row.id)
    all_terminal = True
    required_total = 0
    any_required_failed = False
    for item in scenarios:
        if item.run_id is None:
            all_terminal = False
            continue
        run = _get_run(db, item.run_id, project_id)
        if run is None or run.runtime_status != "FINISHED":
            all_terminal = False
            continue
        if item.required == CampaignScenarioRequired.REQUIRED.value:
            required_total += 1
            if run.outcome in ("BUSINESS_FAIL", "DATA_FAIL", "INCONCLUSIVE"):
                any_required_failed = True

    if not all_terminal:
        # Still running — do not fabricate a terminal campaign.
        return get_campaign(db, row.id, project_id)

    row.status = (
        "PARTIAL" if required_total == 0 or any_required_failed else "COMPLETED"
    )
    db.commit()
    db.refresh(row)
    return get_campaign(db, row.id, project_id)


# ── V35 orchestration wiring (trigger fire / webhook / build diff) ──────────
# These close the §93 "待外部基础设施" orchestration gaps so the Continuous
# Acceptance loop can be driven end-to-end (trigger → build → campaign → gate)
# with idempotent campaign creation and a deterministic build diff.


def fire_trigger(
    db: Session,
    project_id: int,
    trigger_id: int,
    *,
    components: dict[str, Any] | None = None,
    build_label: str | None = None,
    source_type: FingerprintSourceType = FingerprintSourceType.AUTO,
) -> dict[str, Any]:
    """Drive the Continuous Acceptance pipeline once (manual/poll/webhook).

    capture fingerprint → observe build (dedup) → create/return the campaign for
    that build (idempotent — never starts a duplicate campaign for the same build)
    → evaluate the gate. Returns whether the campaign already existed.
    """
    trigger = repository.get_trigger(db, trigger_id, project_id)
    if trigger is None:
        raise APIException(code=404, msg="Trigger 不存在", http_status=404)
    if trigger.status != "ACTIVE":
        raise APIException(code=409, msg="Trigger 已禁用", http_status=409)

    config = _json_dict(trigger.config_json)
    environment_id = int(config.get("environment_id") or 0)
    mission_id = trigger.mission_id or int(config.get("mission_id") or 0)
    if not environment_id or not mission_id:
        raise APIException(code=400, msg="Trigger 缺少 environment/mission 配置", http_status=400)

    fingerprint = capture_fingerprint(
        db,
        environment_id,
        FingerprintCaptureIn(
            components=components or {},
            build_label=build_label,
            source_type=source_type,
        ),
    )
    observation = observe_build(db, environment_id, mission_id, fingerprint["id"])

    # Idempotency: the same BuildObservation never starts a second campaign.
    existing = repository.find_campaign_for_build(db, observation["id"])
    duplicate_campaign = existing is not None
    if existing is not None:
        campaign = get_campaign(db, existing.id, project_id)
    else:
        selection = plan_campaign_selection(db, mission_id, project_id)
        campaign = create_campaign(
            db,
            CampaignCreateIn(
                project_id=project_id,
                mission_id=mission_id,
                environment_id=environment_id,
                name=f"build-{observation['id']}-auto",
                campaign_type=CampaignType.IMPACTED,
                build_observation_id=observation["id"],
                scenarios=selection,
            ),
        )

    repository.update_trigger(db, trigger, {"last_fired_at": datetime.now()})
    # V3.9-R3 (CONT-001): actually RUN the campaign (create real ExecutionRuns and
    # bind them) before the gate is judged. The gate is only final when the
    # campaign reached a terminal state (COMPLETED / PARTIAL).
    campaign_state = start_campaign_execution(db, project_id, campaign["id"])
    gate = evaluate_gate(
        db,
        project_id,
        mission_id,
        campaign["id"],
        observation["id"],
        campaign_status=campaign_state["status"],
    )
    return {
        "fingerprint": fingerprint,
        "build_observation": observation,
        "campaign": campaign_state,
        "gate": gate,
        "duplicate_campaign": duplicate_campaign,
    }


def build_diff(
    db: Session,
    previous_fingerprint_id: int | None,
    current_fingerprint_id: int,
) -> dict[str, Any]:
    """Deterministic change summary between two environment fingerprints.

    Compares service versions + the stable build factors (openapi/db/config/
    static/frontend/build_label) and returns the changed areas. This is the
    deterministic Build Diff used to sanity-check the impact selection (§93 500).
    """
    if previous_fingerprint_id is None:
        return {
            "previous_fingerprint_id": None,
            "current_fingerprint_id": current_fingerprint_id,
            "service_changes": {},
            "changed_areas": ["initial_build"],
            "changed": True,
        }

    prev = repository.get_fingerprint_by_id(db, previous_fingerprint_id)
    curr = repository.get_fingerprint_by_id(db, current_fingerprint_id)
    if prev is None or curr is None:
        return {
            "previous_fingerprint_id": previous_fingerprint_id,
            "current_fingerprint_id": current_fingerprint_id,
            "service_changes": {},
            "changed_areas": ["fingerprint_missing"],
            "changed": prev is None and curr is None,
        }

    prev_c = _json_dict(prev.components_json)
    curr_c = _json_dict(curr.components_json)
    prev_sv = prev_c.get("service_versions") or {}
    curr_sv = curr_c.get("service_versions") or {}
    service_changes: dict[str, dict[str, Any]] = {}
    for key in set(prev_sv) | set(curr_sv):
        old = prev_sv.get(key)
        new = curr_sv.get(key)
        if old != new:
            service_changes[key] = {"from": old, "to": new}

    changed_areas: list[str] = []
    if service_changes:
        changed_areas.append("service_versions")
    for factor in (
        "openapi_hash",
        "db_schema_version",
        "config_hash",
        "static_asset_hash",
        "frontend_version",
    ):
        if prev_c.get(factor) != curr_c.get(factor):
            changed_areas.append(factor)
    if (prev_c.get("build_label") or "") != (curr_c.get("build_label") or ""):
        changed_areas.append("build_label")

    return {
        "previous_fingerprint_id": previous_fingerprint_id,
        "current_fingerprint_id": current_fingerprint_id,
        "service_changes": service_changes,
        "changed_areas": changed_areas,
        "changed": bool(changed_areas or service_changes),
    }
