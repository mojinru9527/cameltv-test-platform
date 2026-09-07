from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import APIException
from app.models.version_task import VersionTask
from app.models.defect import Defect
from app.modules.aitde.contract.models import (
    TestContract as _TestContract,
    TestContractVersion as _TestContractVersion,
)
from app.modules.aitde.execution import defects as run_defects
from app.modules.aitde.ai_closed_loop.models import ScenarioGapCandidate
from app.modules.aitde.continuous.models import (
    BuildObservation,
    ExecutionCampaign,
    QualityGateResultRecord,
)
from app.modules.aitde.execution.models import (
    AssertionResult,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
    ReplayManifest,
)
from app.modules.aitde.intelligence.provider import (
    AiIntelligenceProvider,
    DeterministicScopeProvider,
    ScenarioContext,
)
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario as _TestScenario,
    TestScenarioVersion as _TestScenarioVersion,
)
from app.modules.aitde.scenario.schemas import ScenarioCandidate
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.smart_regression.models import (
    ChangeItem,
    ChangeSet,
    ImpactAnalysisRun,
    LineageEdge,
)
from app.modules.aitde.sources.models import (
    MissionSourceLink,
    SourceArtifact,
    SourceFragment,
)


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


def test_mission_acceptance_cannot_be_marked_pass_directly(db_session):
    mission = mission_service.create_mission(
        db_session,
        {"title": "16.0.0 需求测试", "mission_type": "FEATURE"},
        project_id=1,
        user_id=9,
    )

    with pytest.raises(APIException, match="Quality Gate"):
        mission_service.update_mission(
            db_session,
            mission.id,
            project_id=1,
            data={"acceptance_status": "PASS"},
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


def test_ai_scenario_response_requires_all_three_case_lanes():
    provider = AiIntelligenceProvider(
        db=None,
        project_id=1,
        client=lambda **_kwargs: {"items": [_scenario_payload()]},
    )

    with pytest.raises(Exception, match="missing case lanes: API, FUNCTIONAL"):
        provider.design_scenarios(
            ScenarioContext(
                mission_id=1,
                contract_version_id=2,
                rules=[],
                outcomes=[],
            )
        )


def _execution_run(db, *, project_id: int = 1, outcome: str = "BUSINESS_FAIL"):
    row = ExecutionRun(
        project_id=project_id,
        mission_id=7,
        scenario_id=11,
        scenario_version_id=12,
        contract_version_id=13,
        environment_id=14,
        runtime_status="FINISHED",
        outcome=outcome,
        evidence_status="COMPLETE",
        created_by=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_failed_aitde_run_creates_one_linked_defect(db_session):
    run = _execution_run(db_session)

    first = run_defects.create_for_run(
        db_session, run.id, project_id=1, user_id=9, severity="P1"
    )
    second = run_defects.create_for_run(
        db_session, run.id, project_id=1, user_id=9, severity="P1"
    )

    assert first.id == second.id
    assert first.aitde_run_id == run.id
    assert first.execution_id is None


def test_passed_aitde_run_cannot_create_defect(db_session):
    run = _execution_run(db_session, outcome="PASS")

    with pytest.raises(APIException, match="没有失败结果"):
        run_defects.create_for_run(
            db_session, run.id, project_id=1, user_id=9, severity="P2"
        )


def test_aitde_run_defect_is_project_scoped(db_session):
    run = _execution_run(db_session, project_id=2)

    with pytest.raises(APIException, match="执行记录不存在"):
        run_defects.create_for_run(
            db_session, run.id, project_id=1, user_id=9, severity="P2"
        )


def test_create_defect_from_run_api(client, auth_headers, db_session, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    run = _execution_run(db_session)

    response = client.post(
        f"/api/v2/runs/{run.id}/defects",
        headers=auth_headers,
        json={"severity": "P1", "note": "篮球项目切换后比分未刷新"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["aitde_run_id"] == run.id
    assert data["status"] == "open"


def _seed_lifecycle(db):
    task = _version_task(db, project_id=1, version="16.0.0")
    task.status = "executing"
    mission = Mission(
        project_id=1,
        mission_key="M-1-0034",
        mission_type="FEATURE",
        title="体育平台 16.0.0 篮球多项目适配",
        version_label="16.0.0",
        version_task_id=task.id,
        status="SCENARIO_READY",
        acceptance_status="PASS",
        created_by=1,
    )
    db.add(mission)
    db.flush()
    db.add_all(
        [
            Mission(
                project_id=1,
                mission_key="M-1-0035",
                mission_type="VERSION",
                title="16.0.0 测试环境版本回归",
                version_task_id=task.id,
                created_by=1,
            ),
            Mission(
                project_id=1,
                mission_key="M-1-0036",
                mission_type="REGRESSION",
                title="16.0.0 生产回归",
                version_task_id=task.id,
                created_by=1,
            ),
        ]
    )
    source = SourceArtifact(
        project_id=1,
        source_type="REQUIREMENT",
        name="体育 16.0.0 需求",
        parse_status="PARSED",
        created_by=1,
    )
    db.add(source)
    db.flush()
    db.add(MissionSourceLink(mission_id=mission.id, artifact_id=source.id, is_primary=True))
    db.add(
        ScopeItem(
            mission_id=mission.id,
            scope_key="basketball-project",
            name="篮球多项目适配",
            decision="INCLUDE",
            review_status="APPROVED",
            source_refs_json=f'[{ {"artifact_id": source.id} }]'.replace("'", '"'),
        )
    )
    contract = _TestContract(mission_id=mission.id, name="16.0.0 Contract", current_version_no=1)
    db.add(contract)
    db.flush()
    contract_version = _TestContractVersion(
        contract_id=contract.id,
        version_no=1,
        status="FROZEN",
        snapshot_json="{}",
        created_by=1,
    )
    db.add(contract_version)
    db.flush()
    mission.current_contract_version_id = contract_version.id

    scenario = _TestScenario(
        project_id=1,
        mission_id=mission.id,
        scenario_key="BASKETBALL-UI-001",
        current_version_no=1,
    )
    db.add(scenario)
    db.flush()
    scenario_version = _TestScenarioVersion(
        scenario_id=scenario.id,
        version_no=1,
        contract_version_id=contract_version.id,
        title="切换篮球项目",
        case_type="UI",
        requirement_role="NEW",
        module_key="篮球/项目切换",
        source_refs_json=f'[{ {"artifact_id": source.id} }]'.replace("'", '"'),
        review_status="APPROVED",
        created_by=1,
    )
    db.add(scenario_version)
    db.flush()
    parent = ExecutionRun(
        project_id=1,
        mission_id=mission.id,
        scenario_id=scenario.id,
        scenario_version_id=scenario_version.id,
        contract_version_id=contract_version.id,
        environment_id=5,
        runtime_status="FINISHED",
        outcome="BUSINESS_FAIL",
        evidence_status="COMPLETE",
        created_by=1,
    )
    db.add(parent)
    db.flush()
    child = ExecutionRun(
        project_id=1,
        mission_id=mission.id,
        scenario_id=scenario.id,
        scenario_version_id=scenario_version.id,
        contract_version_id=contract_version.id,
        environment_id=5,
        runtime_status="FINISHED",
        outcome="PASS",
        evidence_status="COMPLETE",
        parent_run_id=parent.id,
        retry_no=1,
        created_by=1,
    )
    db.add(child)
    db.flush()
    db.add(
        EvidenceArtifact(
            project_id=1,
            run_id=parent.id,
            evidence_type="VIDEO",
            storage_uri="evidence/run.mp4",
            content_hash="a" * 64,
            content_type="video/mp4",
            size_bytes=128,
            sanitization_status="SANITIZED",
            integrity_status="VERIFIED",
        )
    )
    db.add(
        Defect(
            project_id=1,
            defect_id="DEF-20260907-001",
            title="项目切换未刷新",
            severity="P1",
            status="pending_review",
            aitde_run_id=parent.id,
            creator_id=1,
        )
    )
    db.commit()
    return mission


def test_mission_lifecycle_exposes_per_case_evidence_defect_and_retest(db_session):
    from app.modules.aitde.mission.lifecycle import build_lifecycle

    mission = _seed_lifecycle(db_session)
    result = build_lifecycle(db_session, mission.id, project_id=1)

    assert result["version_task"]["version"] == "16.0.0"
    assert {phase["mission_type"] for phase in result["phases"]} == {
        "FEATURE",
        "VERSION",
        "REGRESSION",
    }
    assert result["coverage"]["case_types"] == {
        "FUNCTIONAL": 0,
        "API": 0,
        "UI": 1,
        "UNCLASSIFIED": 0,
    }
    case = result["cases"][0]
    assert case["source_ref_count"] == 1
    assert case["run_count"] == 2
    assert case["evidence_count"] == 1
    assert case["defect_count"] == 1
    assert case["retest_count"] == 1
    assert case["retest_status"] == "RETEST_PASSED"
    assert case["latest_outcome"] == "PASS"


def test_mission_lifecycle_rejects_structural_placeholders_as_complete(db_session):
    """A PARSED flag, frozen ``{}``, or evidence URI is not execution proof."""
    from app.modules.aitde.mission.lifecycle import build_lifecycle

    mission = _seed_lifecycle(db_session)
    result = build_lifecycle(db_session, mission.id, project_id=1)

    stages = {stage["key"]: stage for stage in result["stages"]}
    assert stages["sources"]["status"] == "IN_PROGRESS"
    assert stages["contract"]["status"] == "IN_PROGRESS"
    assert stages["cases"]["status"] == "IN_PROGRESS"
    assert stages["execution"]["status"] == "IN_PROGRESS"
    assert stages["acceptance"]["status"] == "NOT_STARTED"
    assert result["mission"]["acceptance_status"] == "NOT_EVALUATED"
    assert result["mission"]["stored_acceptance_status"] == "PASS"
    assert result["mission"]["acceptance_consistent"] is False
    assert result["integrity_status"] == "INCOMPLETE"
    assert result["cases"][0]["execution_complete"] is False


def test_mission_lifecycle_requires_real_fragment_references(db_session):
    from app.modules.aitde.mission.lifecycle import build_lifecycle

    mission = _seed_lifecycle(db_session)
    source = db_session.query(SourceArtifact).filter_by(project_id=1).one()
    db_session.add(
        SourceFragment(
            artifact_id=source.id,
            fragment_key="requirement-1",
            title="篮球多项目切换",
            text="篮球列表支持按项目切换，并保持赛事筛选状态。",
            location_json='{"section":"需求说明"}',
            content_hash="f" * 64,
            sequence=1,
        )
    )
    db_session.commit()

    result = build_lifecycle(db_session, mission.id, project_id=1)

    source_stage = next(stage for stage in result["stages"] if stage["key"] == "sources")
    assert source_stage["status"] == "COMPLETE"
    # The scenario points at fragment id=2, not the persisted fragment, so it
    # must remain incomplete even though the source itself now has a fragment.
    assert result["cases"][0]["source_refs_valid"] is False


def test_mission_lifecycle_is_complete_only_with_real_end_to_end_facts(db_session):
    from app.modules.aitde.mission.lifecycle import build_lifecycle

    mission = _seed_lifecycle(db_session)
    source = db_session.query(SourceArtifact).filter_by(project_id=1).one()
    source.normalized_text = "篮球列表支持项目切换，并保持筛选条件。"
    fragment = SourceFragment(
        artifact_id=source.id,
        fragment_key="requirement-1",
        title="篮球多项目切换",
        text=source.normalized_text,
        location_json='{"section":"需求说明"}',
        content_hash="f" * 64,
        sequence=1,
    )
    db_session.add(fragment)
    db_session.flush()
    source_ref = [{"artifact_id": source.id, "fragment_id": fragment.id}]

    for item in db_session.query(ScopeItem).filter_by(mission_id=mission.id):
        item.reason = "16.0.0 篮球多项目适配需求"
        item.source_refs_json = json.dumps(source_ref)

    contract_version = db_session.get(
        _TestContractVersion, mission.current_contract_version_id
    )
    contract_version.snapshot_json = json.dumps(
        {
            "schema_version": "1.0",
            "mission_id": mission.id,
            "scope_revision": "r1",
            "rules": [
                {
                    "rule_key": "project-switch",
                    "title": "篮球项目切换",
                    "statement": "切换后只展示所选项目赛事",
                    "risk_level": "P1",
                    "source_refs": source_ref,
                }
            ],
            "required_outcomes": [
                {
                    "outcome_key": "selected-project-visible",
                    "statement": "项目名称、赛事列表和请求参数一致",
                    "source_refs": source_ref,
                }
            ],
        },
        ensure_ascii=False,
    )

    existing_version = db_session.query(_TestScenarioVersion).one()
    existing_version.business_goal = "验证页面按篮球项目展示赛事"
    existing_version.given_model_json = '{"project":"默认项目"}'
    existing_version.when_model_json = '{"action":"切换篮球项目"}'
    existing_version.expected_state_json = '{"selected_project":"目标项目"}'
    existing_version.source_refs_json = json.dumps(source_ref)

    for index, case_type in enumerate(("FUNCTIONAL", "API"), start=2):
        scenario = _TestScenario(
            project_id=1,
            mission_id=mission.id,
            scenario_key=f"BASKETBALL-{case_type}-{index:03d}",
            current_version_no=1,
        )
        db_session.add(scenario)
        db_session.flush()
        version = _TestScenarioVersion(
            scenario_id=scenario.id,
            version_no=1,
            contract_version_id=contract_version.id,
            title=f"{case_type} 篮球项目切换",
            business_goal="验证篮球多项目适配",
            case_type=case_type,
            requirement_role="CHANGED" if case_type == "API" else "NEW",
            module_key=f"篮球/{case_type}",
            given_model_json='{"project":"默认项目"}',
            when_model_json='{"action":"切换项目"}',
            expected_state_json='{"project":"目标项目"}',
            source_refs_json=json.dumps(source_ref),
            review_status="APPROVED",
            created_by=1,
        )
        db_session.add(version)
        db_session.flush()
        db_session.add(
            ExecutionRun(
                project_id=1,
                mission_id=mission.id,
                scenario_id=scenario.id,
                scenario_version_id=version.id,
                contract_version_id=contract_version.id,
                environment_id=14,
                runtime_status="FINISHED",
                outcome="PASS",
                evidence_status="COMPLETE",
                created_by=1,
            )
        )
    db_session.flush()

    runs = db_session.query(ExecutionRun).filter_by(mission_id=mission.id).all()
    existing_evidence = db_session.query(EvidenceArtifact).all()
    for artifact in existing_evidence:
        artifact.storage_verified_at = datetime.now()
    existing_evidence_run_ids = {artifact.run_id for artifact in existing_evidence}
    for run in runs:
        db_session.add(
            ExecutionStep(
                run_id=run.id,
                sequence=1,
                step_key="execute-case",
                step_type="API",
                status="SUCCEEDED",
                input_snapshot_json='{"target":"test5"}',
                output_snapshot_json='{"status":"ok"}',
            )
        )
        db_session.add(
            AssertionResult(
                run_id=run.id,
                oracle_id=1,
                expected_json='{"status":"ok"}',
                actual_json='{"status":"ok"}',
                result="PASS",
                reason_code="MATCH",
            )
        )
        if run.id not in existing_evidence_run_ids:
            db_session.add(
                EvidenceArtifact(
                    project_id=1,
                    run_id=run.id,
                    evidence_type="SCREENSHOT",
                    storage_uri=f"evidence/{run.id}.png",
                    content_hash="e" * 64,
                    content_type="image/png",
                    size_bytes=128,
                    sanitization_status="SANITIZED",
                    integrity_status="VERIFIED",
                    storage_verified_at=datetime.now(),
                )
            )
        db_session.add(
            ReplayManifest(
                run_id=run.id,
                schema_version="1.0",
                manifest_json=json.dumps({"run_id": run.id}),
                manifest_hash="r" * 64,
            )
        )

    build = BuildObservation(
        mission_id=mission.id,
        environment_id=14,
        fingerprint_id=1,
        change_summary_json='{"build":"16.0.0-test5"}',
        status="EVALUATED",
    )
    db_session.add(build)
    db_session.flush()
    campaign = ExecutionCampaign(
        project_id=1,
        mission_id=mission.id,
        name="16.0.0 功能测试",
        campaign_type="FULL",
        environment_id=14,
        build_observation_id=build.id,
        status="COMPLETED",
    )
    db_session.add(campaign)
    db_session.flush()
    db_session.add(
        QualityGateResultRecord(
            mission_id=mission.id,
            campaign_id=campaign.id,
            build_observation_id=build.id,
            policy_id=1,
            result="PASS",
            checks_json='[{"gate":"G1","status":"PASS","pass":true}]',
        )
    )

    change_set = ChangeSet(
        project_id=1,
        mission_id=mission.id,
        change_type="PRD",
        status="ANALYZED",
        content_hash="c" * 64,
    )
    db_session.add(change_set)
    db_session.flush()
    db_session.add(
        ChangeItem(
            change_set_id=change_set.id,
            change_kind="CHANGED",
            entity_type="SOURCE_FRAGMENT",
            entity_key=str(fragment.id),
            risk_hint="CONTRACT_RULE",
            source_refs_json=json.dumps(source_ref),
        )
    )
    db_session.add(
        ImpactAnalysisRun(
            project_id=1,
            mission_id=mission.id,
            change_set_id=change_set.id,
            algorithm_version="v1",
            status="COMPLETED",
            input_hash="i" * 64,
            finished_at=datetime.now(),
        )
    )
    db_session.add(
        LineageEdge(
            project_id=1,
            mission_id=mission.id,
            from_type="SOURCE_FRAGMENT",
            from_id=fragment.id,
            to_type="SCENARIO_VERSION",
            to_id=existing_version.id,
            edge_type="DERIVES_FROM",
            source_refs_json=json.dumps(source_ref),
        )
    )
    db_session.add(
        ScenarioGapCandidate(
            mission_id=mission.id,
            gap_type="UNCOVERED_JOURNEY",
            title="跨项目返回状态",
            description="补充返回上一项目时筛选状态保持用例",
            source_refs_json=json.dumps(source_ref),
            evidence_refs_json='[{"run_id": 1}]',
            risk_level="P2",
            confidence=0.81,
            status="OPEN",
        )
    )
    db_session.commit()

    result = build_lifecycle(db_session, mission.id, project_id=1)

    assert result["integrity_status"] == "COMPLETE"
    assert all(stage["status"] == "COMPLETE" for stage in result["stages"])
    assert all(
        stage["status"] == "COMPLETE" for stage in result["supporting_stages"]
    )
    assert result["mission"]["acceptance_status"] == "PASS"
    assert result["coverage"]["case_types"] == {
        "FUNCTIONAL": 1,
        "API": 1,
        "UI": 1,
        "UNCLASSIFIED": 0,
    }
    assert all(case["execution_complete"] for case in result["cases"])


def test_mission_lifecycle_is_project_scoped(db_session):
    from app.modules.aitde.mission.lifecycle import build_lifecycle

    mission = _seed_lifecycle(db_session)

    with pytest.raises(APIException, match="任务不存在"):
        build_lifecycle(db_session, mission.id, project_id=2)


def test_mission_lifecycle_api(client, auth_headers, db_session, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    mission = _seed_lifecycle(db_session)

    response = client.get(
        f"/api/v2/missions/{mission.id}/lifecycle", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["data"]["totals"] == {
        "cases": 1,
        "runs": 2,
        "evidence": 1,
        "verified_evidence": 0,
        "steps": 0,
        "assertions": 0,
        "replays": 0,
        "defects": 1,
        "retests": 1,
        "executed_cases": 1,
    }


def test_mission_change_and_impact_lists_are_persisted_and_project_scoped(
    client, auth_headers, db_session, monkeypatch
):
    from app.core import config

    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    mission = _seed_lifecycle(db_session)
    change_set = ChangeSet(
        project_id=1,
        mission_id=mission.id,
        change_type="PRD",
        status="DETECTED",
        content_hash="c" * 64,
    )
    foreign_change_set = ChangeSet(
        project_id=2,
        mission_id=mission.id,
        change_type="OPENAPI",
        status="DETECTED",
        content_hash="d" * 64,
    )
    db_session.add_all([change_set, foreign_change_set])
    db_session.flush()
    impact_run = ImpactAnalysisRun(
        project_id=1,
        mission_id=mission.id,
        change_set_id=change_set.id,
        algorithm_version="v1",
        status="COMPLETED",
        input_hash="i" * 64,
    )
    db_session.add(impact_run)
    db_session.commit()

    changes = client.get(
        f"/api/v2/missions/{mission.id}/change-sets", headers=auth_headers
    )
    impacts = client.get(
        f"/api/v2/missions/{mission.id}/impact-runs", headers=auth_headers
    )

    assert changes.status_code == 200
    assert [item["id"] for item in changes.json()["data"]["items"]] == [
        change_set.id
    ]
    assert impacts.status_code == 200
    assert [item["id"] for item in impacts.json()["data"]["items"]] == [
        impact_run.id
    ]
