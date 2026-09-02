"""Scenario repository (V30-060..V30-067)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import ReviewStatus, ScenarioReviewStatus
from app.modules.aitde.scenario.models import (
    ScenarioOracleBinding,
    TestOracle,
    TestScenario,
    TestScenarioVersion,
)
from app.modules.aitde.scenario.schemas import OracleCandidate, ScenarioCandidate


def content_hash(candidate: ScenarioCandidate) -> str:
    payload = {
        "given": candidate.given,
        "when": candidate.when,
        "expected": candidate.expected_state,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:32]


def get_scenario(db: Session, scenario_id: int, project_id: int) -> TestScenario | None:
    return db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )


def get_scenario_by_key(
    db: Session, mission_id: int, scenario_key: str
) -> TestScenario | None:
    return db.scalar(
        select(TestScenario).where(
            TestScenario.mission_id == mission_id,
            TestScenario.scenario_key == scenario_key,
        )
    )


def create_or_get_scenario(
    db: Session, project_id: int, mission_id: int, scenario_key: str
) -> TestScenario:
    existing = get_scenario_by_key(db, mission_id, scenario_key)
    if existing:
        return existing
    row = TestScenario(
        project_id=project_id,
        mission_id=mission_id,
        scenario_key=scenario_key,
        current_version_no=1,
    )
    db.add(row)
    db.flush()
    return row


def find_version_by_hash(
    db: Session, scenario_id: int, contract_version_id: int, content_hash: str
) -> TestScenarioVersion | None:
    """按内容哈希查找同一契约版本下已生成的场景版本。

    V4.0 生产黑盒复盘 P1-NEW：场景「重新生成」此前无条件 INSERT 相同
    `(scenario_id, version_no)`，撞唯一约束 `uq_scenario_version_no` 导致 500。
    若同一契约、同一内容哈希的版本已存在，说明内容未变，应复用而非另建版本
    （避免每次点「生成场景」都堆积一个同内容的新版本）。
    """
    return db.scalar(
        select(TestScenarioVersion)
        .where(
            TestScenarioVersion.scenario_id == scenario_id,
            TestScenarioVersion.contract_version_id == contract_version_id,
            TestScenarioVersion.content_hash == content_hash,
        )
        .limit(1)
    )


def create_version(
    db: Session,
    scenario: TestScenario,
    contract_version_id: int,
    candidate: ScenarioCandidate,
    created_by: int,
    created_by_type: str = "AI",
) -> TestScenarioVersion:
    version = TestScenarioVersion(
        scenario_id=scenario.id,
        version_no=scenario.current_version_no,
        contract_version_id=contract_version_id,
        title=candidate.title,
        business_goal=candidate.business_goal,
        priority=candidate.priority.value,
        risk_level=candidate.risk_level.value,
        given_model_json=json.dumps(candidate.given, ensure_ascii=False),
        when_model_json=json.dumps(candidate.when, ensure_ascii=False),
        expected_state_json=json.dumps(candidate.expected_state, ensure_ascii=False),
        source_refs_json=json.dumps(
            [r.model_dump() for r in candidate.source_refs], ensure_ascii=False
        ),
        review_status=ScenarioReviewStatus.PROPOSED.value,
        content_hash=content_hash(candidate),
        created_by=created_by,
        created_by_type=created_by_type,
    )
    db.add(version)
    db.flush()
    replace_oracles(db, version.id, candidate.oracles, created_by_type=created_by_type)
    return version


def replace_oracles(
    db: Session,
    scenario_version_id: int,
    candidates: list[OracleCandidate],
    created_by_type: str = "AI",
) -> list[TestOracle]:
    for old in db.scalars(
        select(TestOracle).where(TestOracle.scenario_version_id == scenario_version_id)
    ).all():
        db.delete(old)
    db.flush()
    rows = []
    for cand in candidates:
        rows.append(
            TestOracle(
                scenario_version_id=scenario_version_id,
                oracle_key=cand.oracle_key,
                oracle_type=cand.oracle_type.value,
                target_json=json.dumps(cand.target, ensure_ascii=False),
                operator=cand.operator,
                expected_value_json=json.dumps(cand.expected_value, ensure_ascii=False),
                source_type=cand.source_type,
                source_refs_json=json.dumps(
                    [r.model_dump() for r in cand.source_refs], ensure_ascii=False
                ),
                required=cand.required,
                confidence=cand.confidence,
                created_by_type=created_by_type,
            )
        )
    db.add_all(rows)
    db.flush()
    return rows


def list_scenarios(db: Session, mission_id: int) -> list[TestScenario]:
    rows = db.scalars(
        select(TestScenario).where(TestScenario.mission_id == mission_id)
    ).all()
    return list(rows)


def current_version(db: Session, scenario_id: int) -> TestScenarioVersion | None:
    return db.scalar(
        select(TestScenarioVersion)
        .where(TestScenarioVersion.scenario_id == scenario_id)
        .order_by(TestScenarioVersion.version_no.desc())
        .limit(1)
    )


def get_version(
    db: Session, scenario_id: int, version_no: int
) -> TestScenarioVersion | None:
    return db.scalar(
        select(TestScenarioVersion).where(
            TestScenarioVersion.scenario_id == scenario_id,
            TestScenarioVersion.version_no == version_no,
        )
    )


def get_version_by_id(db: Session, version_id: int) -> TestScenarioVersion | None:
    return db.get(TestScenarioVersion, version_id)


def list_oracles(db: Session, scenario_version_id: int) -> list[TestOracle]:
    rows = db.scalars(
        select(TestOracle).where(TestOracle.scenario_version_id == scenario_version_id)
    ).all()
    return list(rows)


def upsert_oracle_binding(
    db: Session,
    *,
    scenario_version_id: int,
    oracle_id: int,
    binding_type: str,
    source_step_key: str = "",
    observation_selector_json: str = "{}",
    scenario_adapter_id: int = 0,
) -> ScenarioOracleBinding:
    """Create or re-activate an oracle binding (Batch 207 producer).

    The unique key is (scenario_version_id, oracle_id, binding_type); an    existing row is updated in place (idempotent).
    """
    from datetime import datetime

    row = db.scalar(
        select(ScenarioOracleBinding).where(
            ScenarioOracleBinding.scenario_version_id == scenario_version_id,
            ScenarioOracleBinding.oracle_id == oracle_id,
            ScenarioOracleBinding.binding_type == binding_type,
        )
    )
    if row is None:
        row = ScenarioOracleBinding(
            scenario_version_id=scenario_version_id,
            oracle_id=oracle_id,
            binding_type=binding_type,
            status="ACTIVE",
        )
        db.add(row)
    row.scenario_adapter_id = scenario_adapter_id
    row.source_step_key = source_step_key
    row.observation_selector_json = observation_selector_json
    row.status = "ACTIVE"
    row.validated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return row


def list_oracle_bindings(
    db: Session, scenario_version_id: int | None = None
) -> list[ScenarioOracleBinding]:
    stmt = select(ScenarioOracleBinding).order_by(ScenarioOracleBinding.id.asc())
    if scenario_version_id is not None:
        stmt = stmt.where(
            ScenarioOracleBinding.scenario_version_id == scenario_version_id
        )
    return list(db.scalars(stmt).all())


def review_scenario(
    db: Session,
    version: TestScenarioVersion,
    action: str,
    user_id: int,
    comment: str | None,
) -> TestScenarioVersion:
    version.review_status = action
    if action == ScenarioReviewStatus.APPROVED.value:
        version.approved_by = user_id
        version.approved_at = datetime.now()
    db.commit()
    db.refresh(version)
    return version



def _binding_type_for_observation(observation_type: str, oracle_type: str) -> str | None:
    """Map a plan observation type to an OracleBindingType (C2)."""
    obs = (observation_type or "").upper()
    mapping = {
        "HTTP_STATUS": "API_STATUS",
        "STATUS": "API_STATUS",
        "HTTP_RESPONSE": "API_JSONPATH",
        "RESPONSE": "API_JSONPATH",
        "JSON": "API_JSONPATH",
        "UI_TEXT": "UI_TEXT",
        "TEXT": "UI_TEXT",
        "UI_VISIBLE": "UI_VISIBLE",
        "VISIBLE": "UI_VISIBLE",
        "UI_ATTRIBUTE": "UI_ATTRIBUTE",
        "ATTRIBUTE": "UI_ATTRIBUTE",
        "DB_COLUMN": "DB_COLUMN",
        "COLUMN": "DB_COLUMN",
        "EVENT_FIELD": "EVENT_FIELD",
        "LOG_PATTERN": "LOG_PATTERN",
    }
    if obs in mapping:
        return mapping[obs]
    oracle_map = {
        "API": "API_JSONPATH",
        "DB": "DB_COLUMN",
        "UI": "UI_TEXT",
        "EVENT": "EVENT_FIELD",
        "LOG": "LOG_PATTERN",
    }
    return oracle_map.get((oracle_type or "").upper())


def _observation_selector(oracle: TestOracle, binding_type: str) -> str:
    target = {}
    try:
        target = json.loads(oracle.target_json or "{}")
    except (TypeError, ValueError):
        target = {}
    if binding_type == "API_JSONPATH":
        path = target.get("jsonpath") or target.get("path") or "$"
        return json.dumps({"jsonpath": path}, ensure_ascii=False)
    if binding_type == "DB_COLUMN":
        column = target.get("column") or ""
        return json.dumps({"column": column}, ensure_ascii=False) if column else "{}"
    return json.dumps({}, ensure_ascii=False)


def materialize_bindings_for_plan(db: Session, plan_version_id: int) -> dict:
    """Batch 209 (C2): auto-materialize ACTIVE oracle bindings for a plan.

    For every APPROVED oracle of the plan's scenario version, find the command
    observation whose key matches the oracle_key (or whose command id equals
    it), derive the binding type from the observation type and upsert an ACTIVE
    binding idempotently. Unmatched oracles stay unbound (run fail-fast guards).
    """
    from app.modules.aitde.command.models import CommandPlanVersion

    version = db.get(CommandPlanVersion, plan_version_id)
    if version is None:
        return {"created": 0, "matched": 0}
    try:
        plan = json.loads(version.plan_json or "{}")
    except (TypeError, ValueError):
        plan = {}
    observations: list[dict[str, str]] = []
    for cmd in plan.get("commands") or []:
        command_id = str(cmd.get("id") or "")
        for obs in cmd.get("observations") or []:
            observations.append(
                {
                    "command_id": command_id,
                    "key": str(obs.get("key") or ""),
                    "type": str(obs.get("type") or "").upper(),
                }
            )
    oracles = list(
        db.scalars(
            select(TestOracle).where(
                TestOracle.scenario_version_id == version.scenario_version_id
            )
        ).all()
    )
    created = 0
    matched = 0
    for oracle in oracles:
        if oracle.review_status != ReviewStatus.APPROVED.value:
            continue
        best = None
        for obs in observations:
            key = obs["key"]
            if (
                key == oracle.oracle_key
                or key.endswith(oracle.oracle_key)
                or oracle.oracle_key.endswith(key)
                or obs["command_id"] == oracle.oracle_key
            ):
                best = obs
                break
        if best is None:
            continue
        binding_type = _binding_type_for_observation(best["type"], oracle.oracle_type)
        if binding_type is None:
            continue
        existing = db.scalar(
            select(ScenarioOracleBinding).where(
                ScenarioOracleBinding.scenario_version_id == version.scenario_version_id,
                ScenarioOracleBinding.oracle_id == oracle.id,
                ScenarioOracleBinding.binding_type == binding_type,
            )
        )
        if existing is not None and existing.status == "ACTIVE":
            matched += 1
            continue
        upsert_oracle_binding(
            db,
            scenario_version_id=version.scenario_version_id,
            oracle_id=oracle.id,
            binding_type=binding_type,
            source_step_key=best["command_id"],
            observation_selector_json=_observation_selector(oracle, binding_type),
            scenario_adapter_id=0,
        )
        created += 1
    return {"created": created, "matched": matched}


def review_oracle(
    db: Session,
    oracle: TestOracle,
    action: str,
    user_id: int,
    required: bool | None,
    promote: bool = False,
) -> TestOracle:
    # Oracle Guard: AI_INFERRED cannot directly become an approved REQUIRED
    # oracle UNLESS a human explicitly promotes it (promote=True), which
    # re-sources the oracle as TESTER_APPROVED (Batch 207). The V3.9
    # invariant "AI never silently owns an Outcome" is preserved.
    if oracle.source_type == "AI_INFERRED" and action == ReviewStatus.APPROVED.value:
        if promote:
            oracle.source_type = "TESTER_APPROVED"
            oracle.review_status = ReviewStatus.APPROVED.value
        else:
            oracle.review_status = ReviewStatus.PROPOSED.value
    else:
        oracle.review_status = (
            ReviewStatus.APPROVED.value
            if action == "approve"
            else ReviewStatus.REJECTED.value
        )
    if required is not None:
        oracle.required = required
    oracle.reviewed_by = user_id
    oracle.reviewed_at = datetime.now()
    db.commit()
    db.refresh(oracle)
    return oracle

