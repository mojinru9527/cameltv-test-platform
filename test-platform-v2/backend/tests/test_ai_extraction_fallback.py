"""Regression tests for DeepSeek extraction fallback behavior.

Implemented (2026-07-09, DEV): when the DeepSeek classifier times out or the
network fails, ``extract_features`` degrades to a local, no-LLM module
extraction and returns a reviewable draft (``fallback_used=True``) instead of
raising. Config knobs: ai_timeout_seconds / ai_retry_attempts /
ai_fallback_on_failure. See DEV-test-infra-typefix kanban Batch 4.
"""
from __future__ import annotations

import asyncio

import httpx

from app.core.config import settings
from app.services.ai_service import extract_features


def test_extract_features_falls_back_when_deepseek_times_out(monkeypatch):
    """DeepSeek classifier timeout should return reviewable local modules instead of blocking."""
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_timeout_seconds", 0.01)
    monkeypatch.setattr(settings, "ai_retry_attempts", 1)
    monkeypatch.setattr(settings, "ai_fallback_on_failure", True)

    async def raise_timeout(*_args, **_kwargs):
        """Simulate an intermittent DeepSeek network stall."""
        raise httpx.TimeoutException("classifier stalled")

    monkeypatch.setattr(httpx.AsyncClient, "post", raise_timeout)

    result = asyncio.run(
        extract_features(
            "登录页面\n用户输入手机号和密码\n系统校验账号状态\n登录成功后进入首页",
            file_type="md",
            source_ref="fallback-test.md",
        )
    )

    assert result["fallback_used"] is True
    assert result["modules"]
    assert result["modules"][0]["function_points"]
    assert result["extraction_progress"] == 1.0
