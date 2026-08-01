from __future__ import annotations

import asyncio

import pytest

from app.services.knowledge import skill_service


@pytest.mark.parametrize(
    ("ai_enabled", "ai_api_key", "available", "reason"),
    [
        (False, "configured-key", False, "AI 服务未启用"),
        (True, "", False, "AI_API_KEY 未配置"),
        (True, "configured-key", True, ""),
    ],
)
def test_list_skills_reports_ai_availability(
    monkeypatch, ai_enabled: bool, ai_api_key: str, available: bool, reason: str
):
    monkeypatch.setattr(skill_service.settings, "ai_enabled", ai_enabled)
    monkeypatch.setattr(skill_service.settings, "ai_api_key", ai_api_key)

    skills = skill_service.list_skills()

    assert skills
    assert all(skill["available"] is available for skill in skills)
    assert all(skill["unavailable_reason"] == reason for skill in skills)


@pytest.mark.parametrize(
    ("ai_enabled", "ai_api_key", "reason"),
    [
        (False, "configured-key", "AI 服务未启用"),
        (True, "", "AI_API_KEY 未配置"),
    ],
)
def test_apply_skill_fails_closed_without_ai(
    monkeypatch, ai_enabled: bool, ai_api_key: str, reason: str
):
    monkeypatch.setattr(skill_service.settings, "ai_enabled", ai_enabled)
    monkeypatch.setattr(skill_service.settings, "ai_api_key", ai_api_key)

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
    monkeypatch.setattr(skill_service.settings, "ai_api_key", "configured-key")
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
