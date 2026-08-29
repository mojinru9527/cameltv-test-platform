"""AITDE V3.1 execution run service tests (V31-002)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import EvidenceStatus, RunStatus
from app.modules.aitde.execution import service
from app.modules.aitde.environment import snapshot_service


def _make_snapshot(db, mission_id, **overrides):
    data = {"build_label": "v3.1-test", "service_versions": {"api": "1.0.0"}}
    data.update(overrides)
    return snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=mission_id, project_id=1, data=data
    )


def _run_payload(scenario_graph, snapshot_id):
    return {
        "mission_id": scenario_graph["mission"].id,
        "scenario_id": scenario_graph["scenario"].id,
        "scenario_version_id": scenario_graph["scenario_version"].id,
        "contract_version_id": scenario_graph["contract_version"].id,
        "environment_id": 1,
        "environment_snapshot_id": snapshot_id,
    }


def test_create_run_binds_versions(db, scenario_graph):
    snap = _make_snapshot(db, scenario_graph["mission"].id)
    run = service.create_run(db, _run_payload(scenario_graph, snap.id), project_id=1, user_id=9)
    assert run.scenario_version_id == scenario_graph["scenario_version"].id
    assert run.contract_version_id == scenario_graph["contract_version"].id
    assert run.environment_snapshot_id == snap.id
    assert run.runtime_status == RunStatus.QUEUED.value
    assert run.evidence_status == EvidenceStatus.PENDING.value
    assert run.outcome is None


def test_create_run_rejects_missing_snapshot(db, scenario_graph):
    payload = _run_payload(scenario_graph, None)
    with pytest.raises(APIException) as exc:
        service.create_run(db, payload, project_id=1, user_id=9)
    assert exc.value.http_status == 400
    assert "环境快照" in exc.value.msg


def test_create_run_rejects_cross_project_scenario(db, scenario_graph):
    snap = _make_snapshot(db, scenario_graph["mission"].id)
    payload = _run_payload(scenario_graph, snap.id)
    # run for project 2 against project 1's scenario must be refused
    with pytest.raises(APIException) as exc:
        service.create_run(db, payload, project_id=2, user_id=9)
    assert exc.value.http_status == 400
    assert "不属于当前项目" in exc.value.msg


def test_rejects_illegal_status_transition(db, scenario_graph):
    snap = _make_snapshot(db, scenario_graph["mission"].id)
    run = service.create_run(db, _run_payload(scenario_graph, snap.id), project_id=1, user_id=9)
    with pytest.raises(APIException) as exc:
        service.transition_runtime_status(run, RunStatus.FINISHED.value)
    assert exc.value.http_status == 400
    assert "非法运行状态迁移" in exc.value.msg


def test_allows_running_then_finish(db, scenario_graph):
    snap = _make_snapshot(db, scenario_graph["mission"].id)
    run = service.create_run(db, _run_payload(scenario_graph, snap.id), project_id=1, user_id=9)
    running = service.mark_running(db, run.id, project_id=1)
    assert running.runtime_status == RunStatus.RUNNING.value
    finished = service.finish_run(db, run.id, project_id=1, outcome_str="PASS")
    assert finished.runtime_status == RunStatus.FINISHED.value
    assert finished.outcome == "PASS"
    assert finished.duration_ms is not None


def test_retry_creates_child_run(db, scenario_graph):
    snap = _make_snapshot(db, scenario_graph["mission"].id)
    parent = service.create_run(
        db, _run_payload(scenario_graph, snap.id), project_id=1, user_id=9
    )
    child = service.retry_run(db, parent.id, project_id=1, user_id=9)
    assert child.parent_run_id == parent.id
    assert child.retry_no == 1
    assert child.runtime_status == RunStatus.QUEUED.value
