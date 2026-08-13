"""Batch 167 Phase 3b — 计划一键执行 manual P0/P1 自动转 UI，不再一律 skip。"""
from __future__ import annotations

import json

import pytest

from app.models.environment import Environment
from app.models.test_case import TestCase
from app.models.test_plan import TestPlan, TestPlanCase
from app.services import test_plan_service


@pytest.fixture
def plan_with_case(db_session):
    plan = TestPlan(project_id=1, name="B167-PLAN", status="draft")
    db_session.add(plan)
    db_session.flush()
    case = TestCase(
        project_id=1, title="首页直播列表", module="首页", case_type="manual",
        priority="P0", steps=json.dumps([{"step": 1, "desc": "打开首页", "expected": "看到直播列表"}]),
    )
    db_session.add(case)
    db_session.flush()
    pc = TestPlanCase(plan_id=plan.id, case_id=case.id)
    db_session.add(pc)
    db_session.commit()
    return plan, case, pc


def test_manual_p0_converts_to_ui(plan_with_case, db_session, monkeypatch):
    plan, case, pc = plan_with_case
    monkeypatch.setattr(
        test_plan_service, "_execute_ui_case_sync",
        lambda tc, base_url="": {"ok": True, "total": 1, "screenshots": [], "spec_code": "//spec", "compiler": "llm"},
    )
    monkeypatch.setattr(test_plan_service, "_write_plan_ui_job", lambda *a, **k: None)
    result = test_plan_service.execute_all_cases(db_session, plan.id, project_id=1, auto_ui=True)
    print("RESULT2:", result["details"])
    assert result["skipped"] == 0
    assert result["passed"] == 1
    db_session.refresh(pc)
    assert pc.last_status == "pass"


def test_manual_p2_still_skips(plan_with_case, db_session, monkeypatch):
    plan, case, pc = plan_with_case
    case.priority = "P2"
    db_session.commit()
    called = {"n": 0}
    def fake_exec(tc, base_url=""):
        called["n"] += 1
        return {"ok": True}
    monkeypatch.setattr(test_plan_service, "_execute_ui_case_sync", fake_exec)
    result = test_plan_service.execute_all_cases(db_session, plan.id, project_id=1, auto_ui=True)
    assert result["skipped"] == 1
    assert called["n"] == 0


def test_auto_ui_off_skips(plan_with_case, db_session, monkeypatch):
    plan, case, pc = plan_with_case
    called = {"n": 0}
    def fake_exec(tc, base_url=""):
        called["n"] += 1
        return {"ok": True}
    monkeypatch.setattr(test_plan_service, "_execute_ui_case_sync", fake_exec)
    result = test_plan_service.execute_all_cases(db_session, plan.id, project_id=1, auto_ui=False)
    assert result["skipped"] == 1
    assert called["n"] == 0


def test_ui_case_uses_environment_base_url(plan_with_case, db_session, monkeypatch):
    plan, case, pc = plan_with_case
    case.case_type = "ui"
    env = Environment(project_id=1, name="test", env_type="test", base_url="https://sports.test.example")
    db_session.add(env)
    db_session.commit()
    seen = {}
    def fake_exec(tc, base_url=""):
        seen["base_url"] = base_url
        return {"ok": True, "total": 1, "screenshots": [], "spec_code": "//spec", "compiler": "rules"}
    monkeypatch.setattr(test_plan_service, "_execute_ui_case_sync", fake_exec)
    test_plan_service.execute_all_cases(db_session, plan.id, project_id=1, environment_id=env.id, auto_ui=True)
    assert seen["base_url"] == "https://sports.test.example"


def test_compile_fallback_returns_spec(plan_with_case, monkeypatch):
    plan, case, pc = plan_with_case
    monkeypatch.setattr("app.services.case_compiler_service.compile_to_playwright", lambda *a, **k: {"spec_code": "", "error": "no key"})
    spec, compiler = test_plan_service._compile_ui_case(case, "http://localhost:5173")
    assert compiler == "rules"
    assert "import { test" in spec



