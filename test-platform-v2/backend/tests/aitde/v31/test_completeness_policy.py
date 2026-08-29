"""EvidenceCompletenessPolicy wiring tests (v331-gap A2 / V31-004).

``resolve_evidence_complete`` must decide completeness from the run's
(adapter_type, oracle_type) required evidence set — not merely "some evidence
exists and is sanitized".
"""
from __future__ import annotations

from app.modules.aitde.common.enums import EvidenceType
from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution import repository, service
from app.modules.aitde.execution.service import create_run


def _make_run(db, scenario_graph):
    from app.modules.aitde.environment import snapshot_service

    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=scenario_graph["mission"].id, project_id=1,
        data={"build_label": "v3.1"},
    )
    return create_run(
        db,
        {
            "mission_id": scenario_graph["mission"].id,
            "scenario_id": scenario_graph["scenario"].id,
            "scenario_version_id": scenario_graph["scenario_version"].id,
            "contract_version_id": scenario_graph["contract_version"].id,
            "environment_id": 1,
            "environment_snapshot_id": snap.id,
        },
        project_id=1,
        user_id=9,
    )


def _add_evidence(db, run_id, evidence_type):
    store_artifact(
        db, project_id=1, run_id=run_id, evidence_type=evidence_type,
        data=b"payload", content_type="text/plain",
    )


def _add_scenario_oracle(db, scenario_version_id, oracle_type):
    from app.modules.aitde.scenario.models import TestOracle

    db.add(TestOracle(
        scenario_version_id=scenario_version_id, oracle_key=f"ORACLE-{oracle_type}",
        oracle_type=oracle_type,
    ))
    db.commit()


def test_api_run_complete_with_request_and_response(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    _add_scenario_oracle(db, run.scenario_version_id, "API")
    repository.add_step(db, {
        "run_id": run.id, "sequence": 1, "step_key": "api-1",
        "step_type": "API", "status": "SUCCEEDED",
    })
    _add_evidence(db, run.id, EvidenceType.REQUEST.value)
    _add_evidence(db, run.id, EvidenceType.RESPONSE.value)
    assert service.resolve_evidence_complete(db, run) is True


def test_api_run_missing_response_is_incomplete(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    repository.add_step(db, {
        "run_id": run.id, "sequence": 1, "step_key": "api-1",
        "step_type": "API", "status": "SUCCEEDED",
    })
    _add_evidence(db, run.id, EvidenceType.REQUEST.value)
    assert service.resolve_evidence_complete(db, run) is False


def test_unknown_pair_falls_back_to_conservative_requirement(db, scenario_graph):
    """无 adapter/步骤线索 → 保守要求 RESPONSE+SCREENSHOT，缺一即不完整。"""
    run = _make_run(db, scenario_graph)
    _add_evidence(db, run.id, EvidenceType.RESPONSE.value)
    assert service.resolve_evidence_complete(db, run) is False
    _add_evidence(db, run.id, EvidenceType.SCREENSHOT.value)
    assert service.resolve_evidence_complete(db, run) is True


def test_ui_step_requires_screenshot_and_console(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    _add_scenario_oracle(db, run.scenario_version_id, "UI")
    repository.add_step(db, {
        "run_id": run.id, "sequence": 1, "step_key": "ui-1",
        "step_type": "UI", "status": "SUCCEEDED",
    })
    _add_evidence(db, run.id, EvidenceType.SCREENSHOT.value)
    assert service.resolve_evidence_complete(db, run) is False
    _add_evidence(db, run.id, EvidenceType.CONSOLE.value)
    assert service.resolve_evidence_complete(db, run) is True


def test_legacy_assertion_snapshot_supplies_oracle_type(db, scenario_graph):
    """桥接断言快照携带 oracle_type（API）→ 与 API 步骤匹配出完整要求集。"""
    import json

    run = _make_run(db, scenario_graph)
    step = repository.add_step(db, {
        "run_id": run.id, "sequence": 1, "step_key": "api-1",
        "step_type": "API", "status": "SUCCEEDED",
    })
    repository.add_assertion(db, {
        "run_id": run.id, "step_id": step.id, "oracle_id": 0,
        "oracle_snapshot_json": json.dumps({"source": "legacy_bridge", "oracle_type": "API"}),
        "expected_json": "200", "actual_json": "200", "result": "PASS",
        "reason_code": "legacy_mapped", "evidence_refs_json": "[]",
    })
    _add_evidence(db, run.id, EvidenceType.REQUEST.value)
    _add_evidence(db, run.id, EvidenceType.RESPONSE.value)
    assert service.resolve_evidence_complete(db, run) is True
