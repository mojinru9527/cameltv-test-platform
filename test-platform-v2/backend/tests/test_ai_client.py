"""Batch 208 (C5/C6) — shared LLM client tests."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.core import config
from app.services import ai_client
from app.services.ai_client import (
    AiClientResponseError,
    AiClientUnavailableError,
    achat_completions,
    chat_completions,
    is_configured,
    parse_json_object,
    resolve_config,
)
from app.services.ai_config_service import AIProviderUnconfiguredError

_CFG = SimpleNamespace(model="m", api_base_url="https://ai.test", api_key="k")


class _FakeResponse:
    def __init__(self, content: str, status_code: int = 200):
        self._content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "https://ai.test"), response=self
            )

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeAsyncClient:
    def __init__(self, *a, **k):
        self._results = []

    def set_results(self, results):
        self._results = list(results)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        item = self._results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _cfg_on(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_retry_attempts", 2)
    monkeypatch.setattr(config.settings, "ai_timeout_seconds", 5.0)
    monkeypatch.setattr(
        ai_client.ai_config_service, "resolve", lambda db, pid: _CFG
    )


def test_resolve_config_and_is_configured(monkeypatch):
    assert resolve_config(None, 1) is _CFG
    assert is_configured(None, 1) is True

    def _raise(db, pid):
        raise AIProviderUnconfiguredError("no")

    monkeypatch.setattr(ai_client.ai_config_service, "resolve", _raise)
    assert resolve_config(None, 1) is None
    assert is_configured(None, 1) is False

    monkeypatch.setattr(config.settings, "ai_enabled", False)
    assert resolve_config(None, 1) is None


def test_parse_json_object():
    assert parse_json_object('{"ok": true}') == {"ok": True}
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(AiClientResponseError):
        parse_json_object("not-json")


def test_chat_completions_sync_success(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx,
        "post",
        lambda *a, **k: _FakeResponse(json.dumps({"ok": True})),
    )
    result = chat_completions(
        None, 1, system_prompt="s", user_message="u", json_mode=True
    )
    assert result == {"ok": True}


def test_chat_completions_sync_retries_timeout(monkeypatch):
    calls = {"n": 0}

    def _post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("slow")
        return _FakeResponse(json.dumps({"ok": True}))

    monkeypatch.setattr(ai_client.httpx, "post", _post)
    assert chat_completions(None, 1, system_prompt="s", user_message="u") == {"ok": True}


def test_chat_completions_sync_http_4xx_raises(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx, "post", lambda *a, **k: _FakeResponse("{}", 400)
    )
    with pytest.raises(AiClientUnavailableError):
        chat_completions(None, 1, system_prompt="s", user_message="u")


def test_chat_completions_sync_invalid_json_raises(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx, "post", lambda *a, **k: _FakeResponse("bad")
    )
    with pytest.raises(AiClientResponseError):
        chat_completions(None, 1, system_prompt="s", user_message="u")


def test_chat_completions_raw_mode_returns_text(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx, "post", lambda *a, **k: _FakeResponse("plain")
    )
    out = chat_completions(
        None, 1, system_prompt="s", user_message="u", json_mode=False
    )
    assert out == "plain"


def test_achat_completions_async(monkeypatch):
    fake = _FakeAsyncClient()
    fake.set_results([_FakeResponse(json.dumps({"ok": True}))])
    monkeypatch.setattr(ai_client.httpx, "AsyncClient", lambda *a, **k: fake)

    result = asyncio.run(
        achat_completions(None, 1, system_prompt="s", user_message="u")
    )
    assert result == {"ok": True}
