"""Tests for the LegacyExecutionLink historical backfill tool."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
from app.models.project import Project
from app.models.ui_test import UiTestJob, UiTestRun
from app.modules.aitde.execution.models import ExecutionRun, LegacyExecutionLink

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "backfill_legacy_execution_links.py"
)


@pytest.fixture(scope="module")
def backfill_script():
    spec = importlib.util.spec_from_file_location("backfill_legacy_execution_links", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _legacy_item(
    *,
    task_id: int,
    case_id: int,
    status: str = "passed",
    request: str | None = None,
    response: str | None = None,
    assertions: str | None = None,
) -> ApiExecutionTaskItem:
    return ApiExecutionTaskItem(
        task_id=task_id,
        case_id=case_id,
        status=status,
        request_snapshot=request or json.dumps({"method": "GET", "url": "/health"}),
        response_snapshot=response or json.dumps({"status_code": 200, "body": "{}"}),
        assertion_results=assertions or json.dumps(
            [{"type": "status_code", "expected": 200, "actual": 200, "passed": True}]
        ),
    )


def _task(project_id: int, task_id: str) -> ApiExecutionTask:
    return ApiExecutionTask(
        project_id=project_id,
        task_id=task_id,
        name=task_id,
        total=1,
        status="success",
    )


def test_dry_run_does_not_write(db_session, admin_user, backfill_script):
    task = _task(1, "BACKFILL-DRY")
    db_session.add(task)
    db_session.flush()
    db_session.add(_legacy_item(task_id=task.id, case_id=101))
    db_session.commit()

    plan = backfill_script.build_plan(db_session, project_id=1)
    assert plan["selected_items"] == 1
    assert plan["selected_by_status"] == {"passed": 1}
    assert db_session.query(LegacyExecutionLink).count() == 0
    assert db_session.query(ExecutionRun).count() == 0


def test_apply_is_idempotent_and_backfills_real_evidence(db_session, admin_user, backfill_script):
    task = _task(1, "BACKFILL-APPLY")
    db_session.add(task)
    db_session.flush()
    db_session.add_all(
        [
            _legacy_item(task_id=task.id, case_id=201, status="passed"),
            _legacy_item(
                task_id=task.id,
                case_id=202,
                status="failed",
                assertions=json.dumps(
                    [{"type": "status_code", "expected": 200, "actual": 500, "passed": False}]
                ),
            ),
        ]
    )
    db_session.commit()

    candidates = backfill_script.load_candidates(db_session, project_id=1)
    assert [candidate.status for candidate in candidates] == ["passed", "failed"]
    result = backfill_script.apply_candidates(db_session, candidates)
    assert result == {"created": 2, "already_linked": 0, "failures": []}

    links = db_session.query(LegacyExecutionLink).all()
    assert len(links) == 2
    assert {link.legacy_type for link in links} == {"API_TASK_ITEM"}
    runs = db_session.query(ExecutionRun).filter_by(project_id=1).all()
    assert len(runs) == 2
    assert {run.trigger_type for run in runs} == {"LEGACY_BRIDGE"}
    assert {link.run_id for link in links} == {run.id for run in runs}

    assert backfill_script.load_candidates(db_session, project_id=1) == []
    again = backfill_script.apply_candidates(db_session, [])
    assert again == {"created": 0, "already_linked": 0, "failures": []}
    plan = backfill_script.build_plan(db_session, project_id=1)
    assert plan["selected_items"] == 0
    assert plan["linked_items"] == 2


def test_project_filter_and_bad_json_are_isolated(db_session, admin_user, backfill_script):
    db_session.add(Project(id=2, code="OTHER", name="Other Project", owner_id=admin_user.id, status=1))
    other = _task(2, "BACKFILL-OTHER")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        _legacy_item(
            task_id=other.id,
            case_id=301,
            request="not-json",
            assertions="[bad-json",
        )
    )
    db_session.commit()

    candidates = backfill_script.load_candidates(db_session, project_id=2)
    assert len(candidates) == 1
    assert candidates[0].request == {"legacy_unparseable": True}
    assert candidates[0].assertions == []

    assert backfill_script.load_candidates(db_session, project_id=1) == []
    result = backfill_script.apply_candidates(db_session, candidates)
    assert result["created"] == 1, result
    assert result["failures"] == []
    assert db_session.query(LegacyExecutionLink).count() == 1

def test_ui_run_backfill_is_idempotent(db_session, admin_user, backfill_script):
    job = UiTestJob(project_id=1, name="Historical UI job", environment_id=7)
    db_session.add(job)
    db_session.flush()
    run = UiTestRun(
        job_id=job.id,
        status="fail",
        result=json.dumps({"total": 1, "pass_": 0, "fail": 1}),
        screenshots=json.dumps(["missing-shot.png"]),
        stdout="ui stdout",
        stderr="ui stderr",
    )
    db_session.add(run)
    db_session.commit()

    candidates = backfill_script.load_ui_candidates(db_session, project_id=1)
    assert len(candidates) == 1
    assert candidates[0].status == "fail"
    assert candidates[0].screenshots == ["missing-shot.png"]

    result = backfill_script.apply_ui_candidates(db_session, candidates)
    assert result == {"created": 1, "already_linked": 0, "failures": []}
    link = db_session.query(LegacyExecutionLink).one()
    assert link.legacy_type == "UI_RUN"
    assert link.legacy_id == run.id
    canonical = db_session.query(ExecutionRun).filter_by(id=link.run_id).one()
    assert canonical.project_id == 1
    assert canonical.trigger_type == "LEGACY_BRIDGE"

    assert backfill_script.load_ui_candidates(db_session, project_id=1) == []
    again = backfill_script.apply_ui_candidates(db_session, [])
    assert again == {"created": 0, "already_linked": 0, "failures": []}
