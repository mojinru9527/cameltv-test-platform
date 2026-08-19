"""Batch 170 — UI 执行登录态（storageState）注入回归。"""
from __future__ import annotations

import json
import subprocess

from app.models.environment import Environment, EnvironmentVariable
from app.models.test_case import TestCase
from app.services import test_plan_service


def test_resolve_ui_storage_state_from_encrypted_variable(db_session):
    env = Environment(project_id=1, name="ui-prod", env_type="prod", base_url="https://www.camel1.tv")
    db_session.add(env)
    db_session.flush()
    db_session.add(EnvironmentVariable(
        environment_id=env.id, key="UI_STORAGE_STATE_JSON",
        value=json.dumps({"cookies": [{"name": "auth", "value": "v", "domain": ".camel1.tv"}]}),
        encrypted=False,
    ))
    db_session.commit()
    state = test_plan_service._resolve_ui_storage_state(db_session, env.id, 1)
    assert state is not None
    assert state["cookies"][0]["name"] == "auth"


def test_resolve_ui_storage_state_missing_returns_none(db_session):
    assert test_plan_service._resolve_ui_storage_state(db_session, None, 1) is None
    assert test_plan_service._resolve_ui_storage_state(db_session, 999, 1) is None


def test_execute_ui_injects_storage_state_env(db_session, monkeypatch, tmp_path):
    case = TestCase(
        project_id=1, title="B170-UI", module="首页", case_type="manual", priority="P0",
        steps='[{"step": 1, "desc": "打开首页", "expected": "看到首页"}]',
    )
    db_session.add(case)
    db_session.commit()
    monkeypatch.setattr(
        test_plan_service, "_compile_ui_case",
        lambda db, tc, project_id, base_url: ("import { test, expect } from '@playwright/test';", "llm"),
    )
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        raise subprocess.TimeoutExpired(cmd="npx", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    state = {"cookies": [{"name": "auth", "value": "C_xxx", "domain": ".camel1.tv"}]}
    result = test_plan_service._execute_ui_case_sync(
        None, case, 1, base_url="https://www.camel1.tv", storage_state=state,
    )
    assert result["ok"] is False
    env = captured.get("env") or {}
    assert env.get("PLAYWRIGHT_STORAGE_STATE")
