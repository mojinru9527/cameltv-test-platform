"""Batch 172 — A: ai_service 用例生成 harness 模式单测（mock runner / mock 直连）。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import ai_service


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _ai_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_enabled", False)
    # A2：项目级 AI 配置 —— 打桩 resolve，返回假 EffectiveAiConfig（db 参数可为 None）
    monkeypatch.setattr(
        ai_service.ai_config_service,
        "resolve",
        lambda db, project_id: SimpleNamespace(
            api_base_url="https://api.deepseek.com",
            api_key="sk-test",
            model="deepseek-v4-pro",
        ),
    )
    yield


def _fake_call_ai(monkeypatch, result_dict):
    async def fake(db, project_id, system_prompt, user_message, label="", max_tokens=None):
        return result_dict
    monkeypatch.setattr(ai_service, "_call_ai_api", fake)


def _fake_run_dsh(monkeypatch, final_response="", exit_code=0, error=""):
    def fake(task, **kwargs):
        return SimpleNamespace(
            final_response=final_response,
            exit_code=exit_code,
            error=error,
            session_dir="",
            timed_out=False,
        )
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", fake)


def test_harness_off_keeps_direct_behavior(monkeypatch):
    """use_harness 未开（默认 False）→ 走直连 _call_ai_api，输出与现状一致。"""
    expected = {
        "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
        "functional_cases": [{"title": "case-1"}],
        "api_cases": [],
    }
    _fake_call_ai(monkeypatch, {"result": expected, "raw": "{}", "finish_reason": "completed", "truncated": False, "error": None})

    result = _run(ai_service.generate_test_cases(None, 1, "需求：登录功能", use_harness=False))
    assert result["functional_cases"] == [{"title": "case-1"}]
    assert result["api_cases"] == []


def test_harness_on_uses_runner(monkeypatch):
    """use_harness=True 且 runner 返回合法 JSON → 结果来自 harness 输出。"""
    monkeypatch.setattr(settings, "dsh_enabled", False)  # 显式参数优先于全局开关
    payload = '{"requirement_analysis": {"extracted_requirements": [], "overall_assessment": "ok"}, "functional_cases": [{"title": "harness-case"}], "api_cases": []}'
    _fake_run_dsh(monkeypatch, final_response=payload, exit_code=0)
    # 若走了直连则失败（直连返回空）
    _fake_call_ai(monkeypatch, {"result": None, "raw": "", "finish_reason": "error", "truncated": False, "error": "should not be called"})

    result = _run(ai_service.generate_test_cases(None, 1, "需求：登录功能", use_harness=True))
    assert result["functional_cases"][0]["title"] == "harness-case"
    assert result["api_cases"] == []


def test_harness_failure_falls_back_to_direct(monkeypatch):
    """harness 执行失败 → 自动降级直连，不硬失败。"""
    _fake_run_dsh(monkeypatch, final_response="", exit_code=1, error="boom")
    direct = {
        "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
        "functional_cases": [{"title": "direct-case"}],
        "api_cases": [],
    }
    _fake_call_ai(monkeypatch, {"result": direct, "raw": "{}", "finish_reason": "completed", "truncated": False, "error": None})

    result = _run(ai_service.generate_test_cases(None, 1, "需求：登录功能", use_harness=True))
    assert result["functional_cases"][0]["title"] == "direct-case"


def test_harness_bad_json_falls_back_to_direct(monkeypatch):
    """harness 输出非 JSON → 解析失败降级直连。"""
    _fake_run_dsh(monkeypatch, final_response="not json at all", exit_code=0)
    direct = {
        "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
        "functional_cases": [{"title": "fallback"}],
        "api_cases": [],
    }
    _fake_call_ai(monkeypatch, {"result": direct, "raw": "{}", "finish_reason": "completed", "truncated": False, "error": None})

    result = _run(ai_service.generate_test_cases(None, 1, "需求：登录功能", use_harness=True))
    assert result["functional_cases"][0]["title"] == "fallback"
