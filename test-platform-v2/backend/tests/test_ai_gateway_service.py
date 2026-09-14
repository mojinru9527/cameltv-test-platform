"""Batch 239 — standalone AI Gateway service and remote delegation tests."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

from app.ai_gateway_app import app
from app.core import config
from app.services import ai_client
from app.services.ai_gateway import remote as gateway_remote
from app.services.knowledge.embedding_service import EmbeddingService

client = TestClient(app)


def test_health_is_public_and_reports_role(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_role", "gateway")
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    response = client.get("/internal/ai/v1/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ok"] is True
    assert data["role"] == "gateway"
    assert data["token_configured"] is True


def test_chat_requires_internal_token(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    response = client.post(
        "/internal/ai/v1/chat",
        json={"project_id": 1, "system_prompt": "s", "user_message": "u"},
    )
    assert response.status_code == 401


def test_chat_delegates_to_shared_client(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "gateway")
    monkeypatch.setattr(
        ai_client,
        "chat_completions_full",
        lambda *a, **k: {"content": '{"ok":true}', "model_name": "m"},
    )
    response = client.post(
        "/internal/ai/v1/chat",
        headers={"X-AI-Gateway-Token": "secret"},
        json={
            "project_id": 1,
            "system_prompt": "s",
            "user_message": "u",
            "cache_namespace": "n",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["model_name"] == "m"


def test_embed_returns_vectors(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "gateway")
    monkeypatch.setattr(
        "app.ai_gateway_app.embedding_service.embed",
        lambda texts: np.asarray([[1.0, 0.0]], dtype=np.float32),
    )
    response = client.post(
        "/internal/ai/v1/embed",
        headers={"X-AI-Gateway-Token": "secret"},
        json={"texts": ["hello"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["vectors"] == [[1.0, 0.0]]


def test_remote_client_rejects_recursive_gateway_role(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_url", "http://gw:8100")
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "gateway")
    assert gateway_remote.remote_enabled() is False


def test_ai_client_chat_delegates_remotely(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_gateway_url", "http://gw:8100")
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "remote")
    monkeypatch.setattr(gateway_remote, "remote_requested", lambda: True)
    monkeypatch.setattr(
        gateway_remote,
        "chat_full",
        lambda **kwargs: {"content": "remote", "model_name": "remote-model"},
    )
    monkeypatch.setattr(ai_client, "resolve_route", lambda *a, **k: (_ for _ in ()).throw(AssertionError("local route called")))
    result = ai_client.chat_completions_full(
        None,
        1,
        system_prompt="s",
        user_message="u",
        cache_namespace="n",
    )
    assert result["model_name"] == "remote-model"


def test_embedding_service_uses_remote_gateway(monkeypatch):
    monkeypatch.setattr(gateway_remote, "remote_requested", lambda: True)
    monkeypatch.setattr(gateway_remote, "embed", lambda texts: [[3.0, 4.0]])
    service = EmbeddingService()
    result = service.embed(["hello"])
    assert result is not None
    assert result.shape == (1, 2)
    assert np.allclose(result[0], np.asarray([0.6, 0.8], dtype=np.float32))



def test_ai_client_async_chat_delegates_remotely(monkeypatch):
    import asyncio

    monkeypatch.setattr(gateway_remote, "remote_requested", lambda: True)

    async def _remote(**kwargs):
        return {"content": "remote-async", "model_name": "remote-model"}

    monkeypatch.setattr(gateway_remote, "achat_full", _remote)
    monkeypatch.setattr(ai_client, "resolve_route", lambda *a, **k: (_ for _ in ()).throw(AssertionError("local route called")))
    result = asyncio.run(
        ai_client.achat_completions_full(
            None,
            1,
            system_prompt="s",
            user_message="u",
            cache_namespace="n",
        )
    )
    assert result["content"] == "remote-async"
