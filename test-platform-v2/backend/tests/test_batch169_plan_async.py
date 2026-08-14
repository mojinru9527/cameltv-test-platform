"""Batch 169 — 计划后台执行 + UI 执行超时/编译稳定 回归。"""
from __future__ import annotations

import subprocess

import pytest

from app.models.test_case import TestCase
from app.models.test_plan import TestPlan
from app.services import test_plan_service
from app.services import case_compiler_service


def test_execute_all_async_returns_immediately(db_session, client, auth_headers, monkeypatch):
    plan = TestPlan(project_id=1, name="B169-PLAN", status="draft")
    db_session.add(plan)
    db_session.commit()
    calls = {}

    import app.api.v1.test_plan_execution as tp_module

    def fake_bg(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(tp_module.test_plan_service, "run_async_execute_all", fake_bg)
    resp = client.post(
        f"/api/v1/test-plans/{plan.id}/execute-all",
        headers=auth_headers,
        json={"environment_id": 1, "ui_environment_id": 2, "auto_ui": True, "async_mode": True},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["async"] is True
    assert calls.get("plan_id") == plan.id
    assert calls.get("ui_environment_id") == 2


def test_sync_mode_keeps_old_behavior(db_session, client, auth_headers, monkeypatch):
    plan = TestPlan(project_id=1, name="B169-SYNC", status="draft")
    db_session.add(plan)
    db_session.commit()
    # 无用例计划同步执行返回空结果
    resp = client.post(
        f"/api/v1/test-plans/{plan.id}/execute-all",
        headers=auth_headers,
        json={"environment_id": 1, "auto_ui": False, "async_mode": False},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 0
    assert "async" not in data


def test_ui_timeout_uses_configured_seconds(db_session, monkeypatch):
    monkeypatch.setattr(test_plan_service.settings, "ui_run_timeout_seconds", 7.0)
    case = TestCase(
        project_id=1, title="B169-UI", module="首页", case_type="manual", priority="P0",
        steps='[{"step": 1, "desc": "打开首页", "expected": "看到首页"}]',
    )
    db_session.add(case)
    db_session.commit()

    monkeypatch.setattr(
        test_plan_service, "_compile_ui_case",
        lambda tc, base_url: ("import { test, expect } from '@playwright/test';", "llm"),
    )

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="npx", timeout=7)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = test_plan_service._execute_ui_case_sync(case, base_url="https://www.camel1.tv")
    assert result["ok"] is False
    assert "7s" in result["error"]


def test_compiler_prompt_forbids_networkidle():
    prompt = case_compiler_service.SYSTEM_PROMPT
    assert "waitForLoadState('networkidle')" not in prompt
    assert "setDefaultNavigationTimeout" in prompt
    assert "domcontentloaded" in prompt


def test_execute_all_batch_commit_keeps_results_and_api_task(db_session, monkeypatch):
    """Batch 174（FIX-173-P0-03）：分批短事务提交后，
    - 全部用例都有执行记录（不再依赖末尾单次 commit）；
    - API 用例的任务快照（trigger_type=plan）在中间 commit 后仍正确关联；
    - 汇总数字完整。
    """
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
    from app.models.environment import Environment
    from app.models.test_plan import TestPlanCase

    env = Environment(
        project_id=1, name="B174-ENV", env_type="test",
        base_url="https://httpbin.org",
    )
    db_session.add(env)
    db_session.commit()

    plan = TestPlan(project_id=1, name="B174-BATCH", status="draft")
    db_session.add(plan)
    db_session.commit()

    cases = []
    pcs = []
    for i in range(12):  # > BATCH_COMMIT_SIZE=10，覆盖中途 commit
        case = TestCase(
            project_id=1, title=f"B174-CASE-{i}", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=case.id)
        db_session.add(pc)
        cases.append(case)
        pcs.append(pc)
    db_session.commit()

    fake_result = {"all_pass": True, "status_code": 200, "assertions": []}
    monkeypatch.setattr(
        "app.services.api_execution_service.execute_api_case",
        lambda *a, **k: fake_result,
    )

    result = test_plan_service.execute_all_cases(
        db_session, plan.id,
        executor_id=1, environment_id=env.id, auto_ui=False, project_id=1,
    )

    assert result["total"] == 12
    assert result["passed"] == 12
    assert result["failed"] == 0

    # 全部执行记录已落库（分批 commit 后不再依赖末尾单事务）
    from app.models.test_plan import TestExecution
    exec_rows = db_session.query(TestExecution).filter_by(plan_case_id=pcs[0].id).all()
    assert len(exec_rows) == 1
    assert exec_rows[0].status == "pass"

    # 计划 API 任务快照完整（中间 commit 后 api_task 重新绑定未丢失）
    task = db_session.query(ApiExecutionTask).filter_by(trigger_type="plan").first()
    assert task is not None
    assert task.total == 12
    assert task.passed == 12
    items = db_session.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
    assert len(items) == 12
