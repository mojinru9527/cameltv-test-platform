"""Scenario service (V30-064..V30-070)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import ContractVersionStatus
from app.modules.aitde.contract import repository as contract_repo
from app.modules.aitde.contract.models import TestContract
from app.modules.aitde.intelligence.provider import (
    IntelligenceProvider,
    ScenarioContext,
)
from app.modules.aitde.scenario import repository
from app.modules.aitde.scenario.models import TestOracle
from app.modules.aitde.scenario.schemas import (
    FunctionalProjectionRead,
    OracleReviewRequest,
    ScenarioDesignOutput,
    ScenarioReviewRequest,
)


def _require_frozen_contract(db: Session, contract_version_id: int) -> TestContract:
    version = contract_repo.get_version_by_id(db, contract_version_id)
    if not version:
        raise APIException(code=404, msg="契约版本不存在", http_status=404)
    if version.status != ContractVersionStatus.FROZEN.value:
        raise APIException(
            code=409, msg="CONTRACT_NOT_FROZEN: 契约版本未冻结", http_status=409
        )
    contract = db.get(TestContract, version.contract_id)
    if not contract:
        raise APIException(code=404, msg="Contract 不存在", http_status=404)
    return contract


def generate(
    db: Session,
    contract_version_id: int,
    project_id: int,
    user_id: int,
    provider: IntelligenceProvider | None = None,
) -> dict:
    contract = _require_frozen_contract(db, contract_version_id)
    version = contract_repo.get_version_by_id(db, contract_version_id)
    snapshot = json.loads(version.snapshot_json or "{}")
    rules = snapshot.get("rules", [])
    outcomes = snapshot.get("required_outcomes", [])

    context = ScenarioContext(
        mission_id=contract.mission_id,
        contract_version_id=contract_version_id,
        rules=rules,
        outcomes=outcomes,
    )
    from app.modules.aitde.intelligence.runner import run_intelligence

    if provider is not None:
        output: ScenarioDesignOutput = provider.design_scenarios(context)
        actor = provider.created_by_type
    else:
        output, _op_id, actor = run_intelligence(
            db,
            project_id,
            contract.mission_id,
            "scenario:design",
            lambda prov: prov.design_scenarios(context),
        )

    created = 0
    skipped = 0
    for cand in output.items:
        scenario = repository.create_or_get_scenario(
            db, project_id, contract.mission_id, cand.scenario_key
        )
        content_hash = repository.content_hash(cand)

        # V4.0 生产黑盒复盘 P1-NEW：同一契约下内容未变时复用已有版本，
        # 避免「重新生成」堆积同内容新版本；否则走版本递增。
        existing = repository.find_version_by_hash(
            db, scenario.id, contract_version_id, content_hash
        )
        if existing:
            skipped += 1
            continue

        # 幂等未命中但仍存在旧版本：递增版本号，避免 (scenario_id, version_no) 唯一冲突。
        current = repository.current_version(db, scenario.id)
        if current:
            scenario.current_version_no = current.version_no + 1

        repository.create_version(
            db, scenario, contract_version_id, cand, user_id, created_by_type=actor
        )
        created += 1
    db.commit()
    return {
        "contract_version_id": contract_version_id,
        "scenario_count": created,
        "skipped": skipped,
    }


def list_scenarios(db: Session, mission_id: int, project_id: int) -> list[dict]:
    scenario_repo = repository
    rows = scenario_repo.list_scenarios(db, mission_id)
    result = []
    for s in rows:
        vers = scenario_repo.current_version(db, s.id)
        if not vers:
            continue
        oracles = scenario_repo.list_oracles(db, vers.id)
        result.append(
            {
                "id": s.id,
                "scenario_key": s.scenario_key,
                "title": vers.title,
                "priority": vers.priority,
                "risk_level": vers.risk_level,
                "review_status": vers.review_status,
                "version_no": vers.version_no,
                "oracle_count": len(oracles),
            }
        )
    return result


def get_scenario(db: Session, scenario_id: int, project_id: int) -> dict:
    scenario = repository.get_scenario(db, scenario_id, project_id)
    if not scenario:
        raise APIException(code=404, msg="Scenario 不存在", http_status=404)
    version = repository.current_version(db, scenario.id)
    if not version:
        raise APIException(code=404, msg="Scenario 无版本", http_status=404)
    oracles = repository.list_oracles(db, version.id)
    return {
        "id": scenario.id,
        "scenario_key": scenario.scenario_key,
        "version_no": version.version_no,
        "scenario_version_id": version.id,
        "title": version.title,
        "business_goal": version.business_goal,
        "priority": version.priority,
        "risk_level": version.risk_level,
        "given_model": json.loads(version.given_model_json or "{}"),
        "when_model": json.loads(version.when_model_json or "{}"),
        "expected_state": json.loads(version.expected_state_json or "{}"),
        "review_status": version.review_status,
        "oracles": [_oracle_to_dict(o) for o in oracles],
    }


def review_scenario(
    db: Session,
    scenario_id: int,
    project_id: int,
    user_id: int,
    req: ScenarioReviewRequest,
) -> dict:
    scenario = repository.get_scenario(db, scenario_id, project_id)
    if not scenario:
        raise APIException(code=404, msg="Scenario 不存在", http_status=404)
    version = repository.current_version(db, scenario.id)
    if not version:
        raise APIException(code=404, msg="Scenario 无版本", http_status=404)
    repository.review_scenario(db, version, req.action, user_id, req.comment)
    return {"scenario_id": scenario.id, "review_status": version.review_status}


def review_oracle(
    db: Session, oracle_id: int, user_id: int, req: OracleReviewRequest
) -> dict:
    oracle = db.get(TestOracle, oracle_id)
    if not oracle:
        raise APIException(code=404, msg="Oracle 不存在", http_status=404)
    repository.review_oracle(db, oracle, req.action, user_id, req.required)
    return {"oracle_id": oracle.id, "review_status": oracle.review_status}


def functional_projection(
    db: Session, scenario_id: int, project_id: int
) -> FunctionalProjectionRead:
    scenario = repository.get_scenario(db, scenario_id, project_id)
    if not scenario:
        raise APIException(code=404, msg="Scenario 不存在", http_status=404)
    version = repository.current_version(db, scenario.id)
    if not version:
        raise APIException(code=404, msg="Scenario 无版本", http_status=404)

    given = json.loads(version.given_model_json or "{}")
    when = json.loads(version.when_model_json or "{}")
    expected = json.loads(version.expected_state_json or "{}")

    preconditions = [f"{k} = {v}" for k, v in given.items()] or ["无"]
    action = when.get("action", "执行")
    steps = [
        {"step": 1, "description": f"前置：{'; '.join(preconditions)}"},
        {"step": 2, "description": f"执行：{action}"},
    ]
    expected_results = [f"{k} 应为 {v}" for k, v in expected.items()] or [
        "符合契约预期"
    ]

    return FunctionalProjectionRead(
        scenario_key=scenario.scenario_key,
        title=version.title,
        priority=version.priority,
        preconditions=preconditions,
        steps=steps,
        expected_results=expected_results,
    )


def _oracle_to_dict(o: TestOracle) -> dict:
    return {
        "id": o.id,
        "oracle_key": o.oracle_key,
        "oracle_type": o.oracle_type,
        "target": json.loads(o.target_json or "{}"),
        "operator": o.operator,
        "expected_value": json.loads(o.expected_value_json or "{}"),
        "source_type": o.source_type,
        "required": o.required,
        "confidence": o.confidence,
        "review_status": o.review_status,
    }
