from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.services.ai_config_service import AIProviderUnconfiguredError
from app.services.knowledge import skill_service


def _stub_resolve(monkeypatch, *, configured: bool):
    """项目级 AI 配置打桩：configured=False 时 resolve 抛 AIProviderUnconfiguredError。"""

    def _resolve(db, project_id):
        if not configured:
            raise AIProviderUnconfiguredError()
        return SimpleNamespace(
            provider_id=1,
            provider_name="t",
            provider_type="openai_compatible",
            api_base_url="https://api.deepseek.com",
            api_key="sk-test",
            model="deepseek-v4-pro",
        )

    monkeypatch.setattr(skill_service.ai_config_service, "resolve", _resolve)


@pytest.mark.parametrize(
    ("ai_enabled", "configured", "available", "reason"),
    [
        (False, True, False, "AI 服务未启用"),
        (True, False, False, "当前项目未配置 AI 提供方"),
        (True, True, True, ""),
    ],
)
def test_list_skills_reports_ai_availability(
    monkeypatch, ai_enabled: bool, configured: bool, available: bool, reason: str
):
    monkeypatch.setattr(skill_service.settings, "ai_enabled", ai_enabled)
    _stub_resolve(monkeypatch, configured=configured)

    skills = skill_service.list_skills(None, 1)

    assert skills
    assert all(skill["available"] is available for skill in skills)
    assert all(skill["unavailable_reason"] == reason for skill in skills)


@pytest.mark.parametrize(
    ("ai_enabled", "configured", "reason"),
    [
        (False, True, "AI 服务未启用"),
        (True, False, "当前项目未配置 AI 提供方"),
    ],
)
def test_apply_skill_fails_closed_without_ai(
    monkeypatch, ai_enabled: bool, configured: bool, reason: str
):
    monkeypatch.setattr(skill_service.settings, "ai_enabled", ai_enabled)
    _stub_resolve(monkeypatch, configured=configured)

    result = asyncio.run(
        skill_service.apply_skill_in_new_session(1, "generate-testcases")
    )

    assert result == {
        "success": False,
        "skill": "generate-testcases",
        "error": reason,
    }
    assert "prompt" not in result


def _prepare_configured_skill(monkeypatch):
    from app.core import db as db_module

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setattr(skill_service.settings, "ai_enabled", True)
    _stub_resolve(monkeypatch, configured=True)
    monkeypatch.setattr(db_module, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        skill_service,
        "build_skill_knowledge_context",
        lambda *_args, **_kwargs: "真实体育项目知识",
    )


def test_apply_skill_returns_failure_when_orchestrator_reports_failure(monkeypatch):
    from app.services.knowledge import agent_orchestrator

    _prepare_configured_skill(monkeypatch)
    monkeypatch.setattr(
        agent_orchestrator,
        "run_agent_in_new_session",
        lambda **_kwargs: {"success": False, "error": "上游 AI 执行失败"},
    )

    result = asyncio.run(
        skill_service.apply_skill_in_new_session(1, "generate-testcases")
    )

    assert result == {
        "success": False,
        "skill": "generate-testcases",
        "error": "上游 AI 执行失败",
    }
    assert "prompt" not in result
    assert "knowledge_context" not in result


def test_apply_skill_returns_failure_when_orchestrator_raises(monkeypatch):
    from app.services.knowledge import agent_orchestrator

    _prepare_configured_skill(monkeypatch)

    def raise_unavailable(**_kwargs):
        raise RuntimeError("AI Provider 连接失败")

    monkeypatch.setattr(
        agent_orchestrator,
        "run_agent_in_new_session",
        raise_unavailable,
    )

    result = asyncio.run(
        skill_service.apply_skill_in_new_session(1, "generate-testcases")
    )

    assert result == {
        "success": False,
        "skill": "generate-testcases",
        "error": "Agent 执行异常: AI Provider 连接失败",
    }
    assert "prompt" not in result
    assert "knowledge_context" not in result
