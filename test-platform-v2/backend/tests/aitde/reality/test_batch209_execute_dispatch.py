"""Batch 209 (C1) — execute_commands driver dispatch tests."""
from __future__ import annotations

import json

from app.modules.aitde.command.models import CommandPlanVersion
from app.modules.aitde.execution.models import ExecutionRun, ExecutionStep
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import TestScenarioVersion as _TestScenarioVersion
from app.modules.aitde.workflow import drivers


class _FakeHttpClient:
    def __init__(self, *a, **k):
        pass

    def request(self, *a, **k):
        return _FakeResp()

    def close(self):
        pass


class _FakeResp:
    status_code = 200

    def json(self):
        return {"ok": True}

    @property
    def text(self):
        return "{}"


def _graph(db):
    m = Mission(project_id=1, title="V209", created_by=9)
    db.add(m)
    db.flush()
    sv = _TestScenarioVersion(scenario_id=0, version_no=1, contract_version_id=0)
    db.add(sv)
    db.flush()
    run = ExecutionRun(
        project_id=1,
        mission_id=m.id,
        scenario_id=0,
        scenario_version_id=sv.id,
        contract_version_id=0,
        runtime_status="RUNNING",
        created_by=9,
    )
    db.add(run)
    db.flush()
    plan = CommandPlanVersion(
        command_plan_id=1,
        version_no=1,
        scenario_version_id=sv.id,
        contract_version_id=0,
        schema_version="2.0",
        status="ACTIVE",
        plan_json=json.dumps(
            {
                "schema_version": "2.0",
                "base_url": "http://svc.test",
                "commands": [
                    {
                        "id": "api-1",
                        "driver": "api",
                        "action": "request",
                        "input": {"method": "GET", "path": "/ping"},
                    },
                    {
                        "id": "ui-1",
                        "driver": "browser",
                        "action": "goto",
                        "input": {"route": "/member"},
                    },
                    {
                        "id": "assert-1",
                        "driver": "assertion",
                        "action": "evaluate",
                        "input": {"oracle_key": "o1"},
                    },
                ],
            }
        ),
        generated_by_type="PLANNER",
    )
    db.add(plan)
    db.commit()
    return run


def test_execute_dispatches_api_browser_assertion(db, monkeypatch):
    run = _graph(db)
    monkeypatch.setattr(drivers, "_db", lambda: db)
    monkeypatch.setattr(drivers, "_http", lambda *a, **k: _FakeHttpClient())
    out = drivers._execute_commands_hook({"run_id": run.id, "project_id": 1})
    by_name = {s["name"]: s for s in out["steps"]}
    assert by_name["api-1"]["http_status"] == 200
    assert by_name["api-1"]["ok"] is True
    assert by_name["ui-1"]["ok"] is False
    assert by_name["ui-1"]["error"] == "no_browser_runtime"
    assert by_name["assert-1"]["skipped"] == "assertion_evaluate"
    # a BLOCKED browser ExecutionStep was persisted (no fake HTTP)
    blocked = db.query(ExecutionStep).filter_by(step_key="ui-1").first()
    assert blocked is not None
    assert blocked.status == "FAILED"
    assert blocked.step_type == "BROWSER"


def test_execute_browser_runner_callback(db, monkeypatch):
    run = _graph(db)
    monkeypatch.setattr(drivers, "_db", lambda: db)
    monkeypatch.setattr(drivers, "_http", lambda *a, **k: _FakeHttpClient())

    def fake_runner(ctx, session, seq):
        return {"ok": True, "status": "SUCCEEDED"}

    drivers.register_browser_runner(fake_runner)
    try:
        out = drivers._execute_commands_hook({"run_id": run.id, "project_id": 1})
    finally:
        drivers.register_browser_runner(None)
    by_name = {s["name"]: s for s in out["steps"]}
    assert by_name["ui-1"]["ok"] is True
