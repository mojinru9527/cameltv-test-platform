"""Batch 236 — local runtime and shadow evaluation tests."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.core.db import Base
from app.models.ai_shadow_run import AiShadowRun
from app.services import ai_client
from app.services.ai_gateway import shadow
from app.services.ai_gateway.runtime import LocalRuntimeConfig, runtime_status
from app.services.ai_gateway.shadow import compare_outputs, list_shadow_runs, run_shadow_once, schedule_shadow_run

_CFG = SimpleNamespace(
    provider_id=7,
    provider_name="primary",
    provider_type="openai_compatible",
    model="cloud-model",
    api_base_url="https://ai.test",
    api_key="k",
)


class _FakeResponse:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self._content = content
        self._finish_reason = finish_reason

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {"content": self._content},
                    "finish_reason": self._finish_reason,
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        }


@pytest.fixture()
def shadow_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'shadow.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(shadow, "SessionLocal", Session)
    return Session


def test_runtime_status_does_not_expose_api_key(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_local_runtime_enabled", True)
    monkeypatch.setattr(config.settings, "ai_local_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(config.settings, "ai_local_model", "local-model")
    monkeypatch.setattr(config.settings, "ai_local_api_key", "super-secret")
    status = runtime_status()
    assert status["configured"] is True
    assert status["api_key_configured"] is True
    assert "super-secret" not in json.dumps(status, ensure_ascii=False)
    assert "api_key" not in status


def test_compare_outputs_records_structured_deltas():
    primary = {"content": '{"a":1}', "duration_ms": 100, "usage": {"total_tokens": 12}}
    local = {"content": '{"a":1,"b":2}', "duration_ms": 250, "usage": {"total_tokens": 20}}
    result = compare_outputs(primary, local, json_mode=True)
    assert result["primary_json_valid"] is True
    assert result["shadow_json_valid"] is True
    assert result["exact_match"] is False
    assert result["length_delta"] > 0
    assert result["primary_duration_ms"] == 100
    assert result["shadow_duration_ms"] == 250


def test_schedule_shadow_is_disabled_by_default(monkeypatch):
    submitted = []
    monkeypatch.setattr(shadow._executor, "submit", lambda *a, **k: submitted.append((a, k)))
    monkeypatch.setattr(config.settings, "ai_shadow_enabled", False)
    assert schedule_shadow_run(
        project_id=1,
        primary_config=_CFG,
        namespace="n",
        system_prompt="s",
        user_message="u",
        primary={"content": "{}"},
        max_tokens=100,
        temperature=0.1,
        json_mode=True,
    ) is False
    assert submitted == []


def test_schedule_shadow_sample_rate_and_payload(monkeypatch):
    submitted = []
    monkeypatch.setattr(shadow._executor, "submit", lambda *a, **k: submitted.append((a, k)))
    monkeypatch.setattr(config.settings, "ai_shadow_enabled", True)
    monkeypatch.setattr(config.settings, "ai_shadow_sample_rate", 1.0)
    monkeypatch.setattr(
        shadow,
        "local_runtime_config",
        lambda: LocalRuntimeConfig("http://local/v1", "", "local-model", 30.0, 10000),
    )
    queued = schedule_shadow_run(
        project_id=1,
        primary_config=_CFG,
        namespace="n",
        system_prompt="s",
        user_message="u",
        primary={"content": "{}"},
        max_tokens=100,
        temperature=0.1,
        json_mode=True,
    )
    assert queued is True
    assert len(submitted) == 1
    assert submitted[0][1]["namespace"] == "n"


def test_run_shadow_once_records_success(shadow_db, monkeypatch):
    monkeypatch.setattr(
        shadow,
        "local_runtime_config",
        lambda: LocalRuntimeConfig("http://local/v1", "", "local-model", 30.0, 10000),
    )
    monkeypatch.setattr(
        ai_client,
        "call_configured_full",
        lambda *a, **k: {
            "content": '{"ok":true}',
            "finish_reason": "stop",
            "usage": {"total_tokens": 8},
            "duration_ms": 321,
        },
    )
    run_id = run_shadow_once(
        project_id=1,
        primary_config=_CFG,
        namespace="aitde-cache-v1",
        system_prompt="stable",
        user_message="dynamic",
        primary={
            "content": '{"ok":true}',
            "model_provider": "openai_compatible",
            "model_name": "cloud-model",
            "usage": {"total_tokens": 12},
            "duration_ms": 111,
        },
        max_tokens=100,
        temperature=0.1,
        json_mode=True,
    )
    assert run_id is not None
    with shadow_db() as db:
        row = db.get(AiShadowRun, run_id)
        assert row.status == "succeeded"
        assert row.shadow_model == "local-model"
        assert row.exact_match is True
        assert row.primary_json_valid is True
        assert row.shadow_json_valid is True
        assert row.shadow_duration_ms == 321
        assert list_shadow_runs(db, 1)[0]["id"] == run_id


def test_run_shadow_once_isolates_local_failure(shadow_db, monkeypatch):
    monkeypatch.setattr(
        shadow,
        "local_runtime_config",
        lambda: LocalRuntimeConfig("http://local/v1", "", "local-model", 30.0, 10000),
    )

    def _fail(*a, **k):
        raise ai_client.AiClientUnavailableError("local down")

    monkeypatch.setattr(ai_client, "call_configured_full", _fail)
    run_id = run_shadow_once(
        project_id=1,
        primary_config=_CFG,
        namespace="n",
        system_prompt="s",
        user_message="u",
        primary={"content": "{}", "model_name": "cloud-model"},
        max_tokens=100,
        temperature=0.1,
        json_mode=True,
    )
    with shadow_db() as db:
        row = db.get(AiShadowRun, run_id)
        assert row.status == "failed"
        assert row.error_code == "AiClientUnavailableError"
        assert "local down" in row.error_message


def test_primary_success_schedules_shadow(monkeypatch):
    captured = []
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_retry_attempts", 1)
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", False)
    monkeypatch.setattr(ai_client.ai_config_service, "resolve", lambda db, pid: _CFG)
    monkeypatch.setattr(ai_client.httpx, "post", lambda *a, **k: _FakeResponse('{"ok":true}'))
    monkeypatch.setattr(shadow, "schedule_shadow_run", lambda **kwargs: captured.append(kwargs) or True)

    result = ai_client.chat_completions_full(
        None,
        1,
        system_prompt="stable",
        user_message="dynamic",
        cache_namespace="aitde-cache-v1",
    )
    assert result["content"] == '{"ok":true}'
    assert len(captured) == 1
    assert captured[0]["namespace"] == "aitde-cache-v1"
    assert captured[0]["primary"]["model_name"] == "cloud-model"


def test_runtime_and_shadow_api_are_published():
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/ai-config/runtime" in paths
    assert "/api/v1/ai-config/runtime/health-check" in paths
    assert "/api/v1/ai-config/shadow-runs" in paths

def test_local_runtime_health_check(monkeypatch):
    from app.services.ai_gateway import runtime

    monkeypatch.setattr(config.settings, "ai_local_runtime_enabled", True)
    monkeypatch.setattr(config.settings, "ai_local_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(config.settings, "ai_local_model", "local-model")

    class _Resp:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{"id": "local-model"}]}

    monkeypatch.setattr(runtime.httpx, "get", lambda *a, **k: _Resp())
    health = runtime.check_local_runtime()
    assert health["ok"] is True
    assert health["model_available"] is True
