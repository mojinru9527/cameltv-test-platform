"""Batch 235 — exact-response cache contract tests."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.core.db import Base
from app.services import ai_client
from app.services.ai_gateway.cache import (
    clear_exact_cache,
    exact_cache_stats,
    lookup_exact_cache,
    store_exact_cache,
)
from app.services.ai_gateway.keys import build_cache_key

_CFG = SimpleNamespace(
    provider_id=7,
    provider_name="test",
    provider_type="local_openai_compatible",
    model="local-model",
    api_base_url="http://127.0.0.1:11434/v1",
    api_key="dummy",
)


class _FakeResponse:
    def __init__(self, content: str, *, finish_reason: str = "stop", usage=None):
        self._content = content
        self._finish_reason = finish_reason
        self._usage = usage

    def raise_for_status(self) -> None:
        return None

    def json(self):
        data = {
            "choices": [
                {
                    "message": {"content": self._content},
                    "finish_reason": self._finish_reason,
                }
            ]
        }
        if self._usage is not None:
            data["usage"] = self._usage
        return data


@pytest.fixture()
def cache_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cache.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_retry_attempts", 1)
    monkeypatch.setattr(config.settings, "ai_timeout_seconds", 5.0)
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", True)
    monkeypatch.setattr(config.settings, "ai_exact_cache_ttl_seconds", 3600)
    monkeypatch.setattr(ai_client.ai_config_service, "resolve", lambda db, pid: _CFG)


def _post_counter(calls, *, finish_reason="stop", usage=None):
    def _post(*args, **kwargs):
        calls.append(kwargs["json"])
        return _FakeResponse(
            json.dumps({"ok": True}),
            finish_reason=finish_reason,
            usage=usage
            or {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
            },
        )

    return _post


def test_exact_cache_reuses_response_and_records_hit(cache_db, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_client.httpx, "post", _post_counter(calls))

    first = ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="stable system",
        user_message="same input",
        cache_namespace="aitde-cache-v1",
    )
    second = ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="stable system",
        user_message="same input",
        cache_namespace="aitde-cache-v1",
    )

    assert first["cache_status"] == "write"
    assert second["cache_status"] == "hit"
    assert second["usage"] == {}
    assert second["cache_saved_usage"]["total_tokens"] == 12
    assert len(calls) == 1
    stats = exact_cache_stats(cache_db, 1)
    assert stats["entries"] == 1
    assert stats["active_entries"] == 1
    assert stats["hit_count"] == 1


def test_exact_cache_is_project_scoped(cache_db, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_client.httpx, "post", _post_counter(calls))
    for project_id in (1, 2):
        ai_client.chat_completions_full(
            cache_db,
            project_id,
            system_prompt="s",
            user_message="u",
            cache_namespace="scope-v1",
        )
    assert len(calls) == 2
    assert exact_cache_stats(cache_db, 1)["entries"] == 1
    assert exact_cache_stats(cache_db, 2)["entries"] == 1


def test_truncated_response_is_not_cached(cache_db, monkeypatch):
    calls = []
    monkeypatch.setattr(
        ai_client.httpx,
        "post",
        _post_counter(calls, finish_reason="length"),
    )
    first = ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="aitde-cache-v1",
    )
    second = ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="aitde-cache-v1",
    )
    assert first["cache_status"] == "bypass_truncated"
    assert second["cache_status"] == "bypass_truncated"
    assert len(calls) == 2
    assert exact_cache_stats(cache_db, 1)["entries"] == 0


def test_cache_disabled_preserves_legacy_behavior(cache_db, monkeypatch):
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", False)
    calls = []
    monkeypatch.setattr(ai_client.httpx, "post", _post_counter(calls))
    for _ in range(2):
        result = ai_client.chat_completions_full(
            cache_db,
            1,
            system_prompt="s",
            user_message="u",
            cache_namespace="aitde-cache-v1",
        )
        assert result["cache_status"] == "disabled"
    assert len(calls) == 2


def test_expired_entry_is_a_miss(cache_db, monkeypatch):
    monkeypatch.setattr(config.settings, "ai_exact_cache_ttl_seconds", 0)
    calls = []
    monkeypatch.setattr(ai_client.httpx, "post", _post_counter(calls))
    ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="expiry-v1",
    )
    ai_client.chat_completions_full(
        cache_db,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="expiry-v1",
    )
    assert len(calls) == 2


def test_clear_cache_can_target_one_namespace(cache_db):
    key_a = build_cache_key(
        project_id=1,
        provider_id=7,
        model="m",
        namespace="a",
        system_prompt="s",
        user_message="u",
        json_mode=True,
        max_tokens=100,
        temperature=0.1,
    )
    key_b = build_cache_key(
        project_id=1,
        provider_id=7,
        model="m",
        namespace="b",
        system_prompt="s",
        user_message="u",
        json_mode=True,
        max_tokens=100,
        temperature=0.1,
    )
    store_exact_cache(
        cache_db,
        project_id=1,
        namespace="a",
        cache_key=key_a,
        provider_id=7,
        provider_type="openai_compatible",
        model="m",
        prompt_hash="p",
        input_hash="i",
        response={"content": "{}", "finish_reason": "stop", "usage": {}},
    )
    store_exact_cache(
        cache_db,
        project_id=1,
        namespace="b",
        cache_key=key_b,
        provider_id=7,
        provider_type="openai_compatible",
        model="m",
        prompt_hash="p",
        input_hash="i",
        response={"content": "{}", "finish_reason": "stop", "usage": {}},
    )
    assert clear_exact_cache(cache_db, 1, namespace="a") == 1
    assert exact_cache_stats(cache_db, 1)["namespaces"] == ["b"]


def test_malformed_cached_payload_is_deleted(cache_db):
    key = build_cache_key(
        project_id=1,
        provider_id=7,
        model="m",
        namespace="bad",
        system_prompt="s",
        user_message="u",
        json_mode=True,
        max_tokens=100,
        temperature=0.1,
    )
    from app.models.ai_gateway_cache import AiResponseCache

    cache_db.add(
        AiResponseCache(
            project_id=1,
            namespace="bad",
            cache_key=key,
            provider_id=7,
            provider_type="openai_compatible",
            model="m",
            response_json="not-json",
        )
    )
    cache_db.commit()
    assert lookup_exact_cache(cache_db, project_id=1, cache_key=key) is None
    assert exact_cache_stats(cache_db, 1)["entries"] == 0

def test_cache_api_is_published_in_openapi():
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/ai-config/cache-stats" in paths
    assert "/api/v1/ai-config/cache" in paths

