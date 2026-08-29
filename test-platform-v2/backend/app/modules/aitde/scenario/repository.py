"""Scenario repository (V30-060..V30-067)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import ReviewStatus, ScenarioReviewStatus
from app.modules.aitde.scenario.models import (
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


def create_version(
    db: Session,
    scenario: TestScenario,
    contract_version_id: int,
    candidate: ScenarioCandidate,
    created_by: int,
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
        created_by_type="AI",
    )
    db.add(version)
    db.flush()
    replace_oracles(db, version.id, candidate.oracles)
    return version


def replace_oracles(
    db: Session, scenario_version_id: int, candidates: list[OracleCandidate]
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
                created_by_type="AI",
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


def review_oracle(
    db: Session, oracle: TestOracle, action: str, user_id: int, required: bool | None
) -> TestOracle:
    # Oracle Guard: AI_INFERRED cannot directly become an approved REQUIRED oracle.
    if oracle.source_type == "AI_INFERRED" and action == ReviewStatus.APPROVED.value:
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
