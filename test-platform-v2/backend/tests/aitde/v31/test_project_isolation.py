"""Project isolation contract tests (v331-gap C4 / V30-121).

AITDE execution surfaces must honour the tenant boundary: reads scoped by
``project_id``, legacy bridge payloads resolvable only inside the owning
project, cross-project linking rejected.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import LegacyExecutionType
from app.modules.aitde.execution import legacy_bridge, repository
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


def _seed_api_item(db, project_id=1):
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

    task = ApiExecutionTask(project_id=project_id, total=1)
    db.add(task)
    db.flush()
    item = ApiExecutionTaskItem(
        task_id=task.id, case_id=1, status="passed",
        request_snapshot='{"method":"GET"}', response_snapshot='{"status_code":200}',
        assertion_results='[{"type":"status_code","passed":true}]',
    )
    db.add(item)
    db.commit()
    return item, task


def _seed_ui_run(db, project_id=1):
    from app.models.ui_test import UiTestJob, UiTestRun

    job = UiTestJob(project_id=project_id)
    db.add(job)
    db.flush()
    run = UiTestRun(job_id=job.id, status="passed", screenshots='["a.png"]')
    db.add(run)
    db.commit()
    return run, job


# ── run-scoped reads ─────────────────────────────────────────────────────────


def test_run_scoped_reads_hide_cross_project(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    repository.add_step(db, {
        "run_id": run.id, "sequence": 1, "step_key": "s", "step_type": "API",
        "status": "SUCCEEDED",
    })
    assert repository.list_steps(db, run.id, 1) != []
    assert repository.list_steps(db, run.id, 2) == []
    assert repository.list_assertions(db, run.id, 2) == []
    assert repository.list_evidence(db, run.id, 2) == []
    assert repository.get_run(db, run.id, 2) is None


# ── legacy loaders (v2 link endpoint seam) ──────────────────────────────────


def test_api_item_loader_enforces_project(db):
    item, task = _seed_api_item(db, project_id=1)
    loaded_item, loaded_task = legacy_bridge.load_api_item_for_project(db, item.id, 1)
    assert loaded_item.id == item.id
    assert loaded_task.id == task.id
    with pytest.raises(APIException) as exc:
        legacy_bridge.load_api_item_for_project(db, item.id, 2)
    assert exc.value.http_status == 404
    with pytest.raises(APIException):
        legacy_bridge.load_api_item_for_project(db, 999999, 1)


def test_ui_run_loader_enforces_project(db):
    run, job = _seed_ui_run(db, project_id=1)
    loaded_run, loaded_job = legacy_bridge.load_ui_run_for_project(db, run.id, 1)
    assert loaded_run.id == run.id
    assert loaded_job.id == job.id
    with pytest.raises(APIException) as exc:
        legacy_bridge.load_ui_run_for_project(db, run.id, 2)
    assert exc.value.http_status == 404
    with pytest.raises(APIException):
        legacy_bridge.load_ui_run_for_project(db, 999999, 1)


# ── bridge link tenant boundary ──────────────────────────────────────────────


def test_bridge_link_rejects_cross_project_run(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    with pytest.raises(APIException) as exc:
        legacy_bridge.bridge_api_item(
            db, project_id=2, run_id=run.id, legacy_id=1001, request={"x": 1},
        )
    assert exc.value.http_status == 404
    # 被拒绝的桥接不得留下任何链接或步骤
    assert legacy_bridge.find_link(db, LegacyExecutionType.API_TASK_ITEM, 1001) is None
    assert repository.list_steps(db, run.id, 1) == []


def test_bridge_ui_rejects_cross_project_run(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    with pytest.raises(APIException) as exc:
        legacy_bridge.bridge_ui_run(
            db, project_id=2, run_id=run.id, legacy_id=1002, screenshots=["a.png"],
        )
    assert exc.value.http_status == 404
    assert legacy_bridge.find_link(db, LegacyExecutionType.UI_RUN, 1002) is None
