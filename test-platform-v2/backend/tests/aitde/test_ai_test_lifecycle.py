from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.exceptions import APIException
from app.models.version_task import VersionTask
from app.modules.aitde.intelligence.provider import (
    AiIntelligenceProvider,
    DeterministicScopeProvider,
    ScenarioContext,
)
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.scenario.schemas import ScenarioCandidate


def _version_task(db, *, project_id: int, version: str) -> VersionTask:
    row = VersionTask(
        project_id=project_id,
        title=f"版本 {version}",
        version=version,
        created_by=1,
        qa_owner_id=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _scenario_payload(**overrides):
    payload = {
        "scenario_key": "BASKETBALL-001",
        "title": "篮球多项目切换",
        "business_goal": "用户能在多个篮球项目间切换",
        "priority": "P1",
        "risk_level": "P1",
        "case_type": "UI",
        "requirement_role": "NEW",
        "module_key": "篮球/项目切换",
        "given": {"project": "A"},
        "when": {"action": "switch_project"},
        "expected_state": {"project": "B"},
        "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
        "oracles": [],
    }
    payload.update(overrides)
    return payload


def test_mission_can_link_same_project_version_task(db_session):
    task = _version_task(db_session, project_id=1, version="16.0.0")

    mission = mission_service.create_mission(
        db_session,
        {
            "title": "16.0.0 需求测试",
            "mission_type": "FEATURE",
            "version_task_id": task.id,
        },
        project_id=1,
        user_id=9,
    )

    assert mission.version_task_id == task.id


def test_mission_rejects_cross_project_version_task(db_session):
    foreign_task = _version_task(db_session, project_id=2, version="16.0.0")

    with pytest.raises(APIException, match="版本任务不存在"):
        mission_service.create_mission(
            db_session,
            {"title": "越权任务", "version_task_id": foreign_task.id},
            project_id=1,
            user_id=9,
        )


@pytest.mark.parametrize("missing", ["case_type", "requirement_role", "module_key"])
def test_scenario_candidate_requires_traceability_fields(missing):
    payload = _scenario_payload()
    payload.pop(missing)

    with pytest.raises(ValidationError):
        ScenarioCandidate.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [("case_type", "scenario"), ("requirement_role", "legacy")],
)
def test_scenario_candidate_rejects_unknown_classification(field, invalid):
    with pytest.raises(ValidationError):
        ScenarioCandidate.model_validate(_scenario_payload(**{field: invalid}))


def test_deterministic_scenarios_are_explicitly_classified():
    output = DeterministicScopeProvider().design_scenarios(
        ScenarioContext(
            mission_id=1,
            contract_version_id=2,
            rules=[
                {
                    "rule_key": "basketball-project",
                    "title": "篮球项目切换",
                    "statement": "切换后展示目标项目",
                    "risk_level": "P1",
                    "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
                }
            ],
            outcomes=[],
        )
    )

    scenario = output.items[0]
    assert scenario.case_type == "FUNCTIONAL"
    assert scenario.requirement_role == "CHANGED"
    assert scenario.module_key == "篮球项目切换"


def test_ai_scenario_response_missing_classification_fails_closed():
    provider = AiIntelligenceProvider(
        db=None,
        project_id=1,
        client=lambda **_kwargs: {"items": [_scenario_payload()]},
    )
    invalid = _scenario_payload()
    invalid.pop("case_type")
    provider._client = lambda **_kwargs: {"items": [invalid]}

    with pytest.raises(Exception, match="invalid item"):
        provider.design_scenarios(
            ScenarioContext(
                mission_id=1,
                contract_version_id=2,
                rules=[],
                outcomes=[],
            )
        )
