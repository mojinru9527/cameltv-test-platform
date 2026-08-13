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

    import app.api.v1.test_plan as tp_module

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
