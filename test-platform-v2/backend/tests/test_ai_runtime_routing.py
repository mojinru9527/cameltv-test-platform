"""Batch 237 — local-first routing and cloud fallback tests."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core import config
from app.core.db import Base
from app.models.ai_shadow_run import AiShadowRun
from app.services import ai_client
from app.services.ai_gateway.router import LocalRuntimeUnavailableError, RoutePlan, build_route

_CLOUD = SimpleNamespace(
    provider_id=1,
    provider_name="cloud",
    provider_type="openai_compatible",
    model="cloud-model",
    api_base_url="https://cloud.test",
    api_key="cloud-key",
    timeout_seconds=30.0,
)
_LOCAL = SimpleNamespace(
    provider_id=0,
    provider_name="local",
    provider_type="local_openai_compatible",
    model="local-model",
    api_base_url="http://127.0.0.1:11434/v1",
    api_key="",
    timeout_seconds=30.0,
)


def _summary(model: str, content: str = '{"ok":true}'):
    return {
        "content": content,
        "finish_reason": "stop",
        "truncated": False,
        "usage": {"total_tokens": 10},
        "model_provider": "local_openai_compatible" if model == "local-model" else "openai_compatible",
        "model_name": model,
        "duration_ms": 50,
    }


def test_build_route_cloud_only_has_no_shadow_or_fallback():
    plan = build_route(cloud=_CLOUD, mode="cloud_only", shadow_enabled=False)
    assert plan.primary_origin == "cloud"
    assert plan.primary_config is _CLOUD
    assert plan.shadow_config is None
    assert plan.fallback_config is None


def test_build_route_shadow_uses_local_as_observation(monkeypatch):
    import app.services.ai_gateway.router as router

    monkeypatch.setattr(
        router,
        "local_runtime_config",
        lambda: SimpleNamespace(as_ai_config=lambda: _LOCAL),
    )
    plan = build_route(cloud=_CLOUD, mode="shadow", shadow_enabled=True)
    assert plan.primary_config is _CLOUD
    assert plan.shadow_config is _LOCAL
    assert plan.fallback_config is None


def test_build_route_local_preferred_has_cloud_fallback(monkeypatch):
    import app.services.ai_gateway.router as router

    monkeypatch.setattr(config.settings, "ai_local_fallback_to_cloud", True)
    monkeypatch.setattr(
        router,
        "local_runtime_config",
        lambda: SimpleNamespace(as_ai_config=lambda: _LOCAL),
    )
    plan = build_route(cloud=_CLOUD, mode="local_preferred", shadow_enabled=True)
    assert plan.primary_config is _LOCAL
    assert plan.fallback_config is _CLOUD
    assert plan.shadow_config is _CLOUD
    assert plan.primary_origin == "local"


def test_build_route_local_only_requires_local_runtime(monkeypatch):
    import app.services.ai_gateway.router as router

    monkeypatch.setattr(router, "local_runtime_config", lambda: None)
    with pytest.raises(LocalRuntimeUnavailableError):
        build_route(cloud=_CLOUD, mode="local_only", shadow_enabled=False)


def test_local_preferred_uses_local_primary(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", False)
    monkeypatch.setattr(
        ai_client,
        "resolve_route",
        lambda db, pid, namespace="": RoutePlan(
            mode="local_preferred",
            primary_origin="local",
            primary_config=_LOCAL,
            fallback_config=_CLOUD,
            fallback_origin="cloud",
        ),
    )
    monkeypatch.setattr(
        ai_client,
        "_call_configured_full",
        lambda cfg, **kwargs: _summary(cfg.model),
    )
    result = ai_client.chat_completions_full(
        None,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="route-v1",
    )
    assert result["model_name"] == "local-model"
    assert result["route_status"] == "primary"
    assert result["route_origin"] == "local"


def test_local_preferred_falls_back_to_cloud(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", False)
    monkeypatch.setattr(
        ai_client,
        "resolve_route",
        lambda db, pid, namespace="": RoutePlan(
            mode="local_preferred",
            primary_origin="local",
            primary_config=_LOCAL,
            fallback_config=_CLOUD,
            fallback_origin="cloud",
        ),
    )
    calls = []

    def _call(cfg, **kwargs):
        calls.append(cfg.model)
        if cfg.model == "local-model":
            raise ai_client.AiClientUnavailableError("local down")
        return _summary(cfg.model)

    monkeypatch.setattr(ai_client, "_call_configured_full", _call)
    result = ai_client.chat_completions_full(
        None,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="route-v1",
    )
    assert calls == ["local-model", "cloud-model"]
    assert result["model_name"] == "cloud-model"
    assert result["route_status"] == "fallback"
    assert result["route_fallback_from"] == "local"


def test_async_local_preferred_falls_back_to_cloud(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_exact_cache_enabled", False)
    monkeypatch.setattr(
        ai_client,
        "resolve_route",
        lambda db, pid, namespace="": RoutePlan(
            mode="local_preferred",
            primary_origin="local",
            primary_config=_LOCAL,
            fallback_config=_CLOUD,
            fallback_origin="cloud",
        ),
    )
    calls = []

    async def _call(cfg, **kwargs):
        calls.append(cfg.model)
        if cfg.model == "local-model":
            raise ai_client.AiClientUnavailableError("local down")
        return _summary(cfg.model)

    monkeypatch.setattr(ai_client, "_acall_configured_full", _call)
    result = asyncio.run(
        ai_client.achat_completions_full(
            None,
            1,
            system_prompt="s",
            user_message="u",
            cache_namespace="route-v1",
        )
    )
    assert calls == ["local-model", "cloud-model"]
    assert result["route_status"] == "fallback"

def test_shadow_policy_recommends_local_preferred_when_evidence_passes(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.services.ai_gateway.policy import evaluate_shadow_policy

    engine = create_engine(f"sqlite:///{tmp_path / 'policy.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for _ in range(3):
            db.add(AiShadowRun(
                project_id=1,
                namespace="n",
                status="succeeded",
                shadow_json_valid=True,
                exact_match=True,
                primary_duration_ms=100,
                shadow_duration_ms=150,
            ))
        db.commit()
        result = evaluate_shadow_policy(db, 1, namespace="n", min_samples=3)
    assert result["recommendation"] == "local_preferred"
    assert result["exact_match_rate"] == 1.0


def test_is_configured_uses_active_local_route(monkeypatch):
    monkeypatch.setattr(ai_client, "resolve_route", lambda db, pid: RoutePlan(
        mode="local_only",
        primary_origin="local",
        primary_config=_LOCAL,
    ))
    assert ai_client.is_configured(None, 1) is True
