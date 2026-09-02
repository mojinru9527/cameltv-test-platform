"""Batch 209 (C6b) — agent project-level AI gate tests."""
from __future__ import annotations

from app.api.v1.agent import _agent_unavailable_reason
from app.core import config
from app.services import ai_client


def test_env_fallback_without_db(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_api_key", "")
    assert _agent_unavailable_reason(None, 0) == "AI_API_KEY 未配置"

    monkeypatch.setattr(config.settings, "ai_api_key", "k")
    assert _agent_unavailable_reason(None, 0) == ""


def test_global_kill_switch(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", False)
    assert _agent_unavailable_reason(None, 0) == "AI 服务未启用"


def test_project_configured_wins(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_api_key", "")
    monkeypatch.setattr(ai_client, "is_configured", lambda db, pid: True)
    assert _agent_unavailable_reason(object(), 1) == ""


def test_project_unconfigured_blocks(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_api_key", "env-key-set-but-project-missing")
    monkeypatch.setattr(ai_client, "is_configured", lambda db, pid: False)
    reason = _agent_unavailable_reason(object(), 1)
    assert "项目未配置" in reason
