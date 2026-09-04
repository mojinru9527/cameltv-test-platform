"""Worker heartbeat authentication through least-privilege API Tokens."""
from __future__ import annotations

from app.core import config
from app.models.api_token import ApiToken


def _heartbeat(worker_key: str) -> dict[str, object]:
    return {
        "worker_key": worker_key,
        "name": "Test5 Worker",
        "network_zone": "TEST",
        "version": "1.0",
        "machine_identity": "test5-node",
        "tags": {"host": "test5-node"},
        "capabilities": ["HTTP", "BROWSER"],
    }


def _create_token(client, auth_headers: dict[str, str], scopes: list[str]) -> dict:
    response = client.post(
        "/api/v1/tokens",
        json={"name": "Worker registration", "scopes": scopes},
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_worker_scoped_token_registers_without_user_cookie_or_project_header(
    client, auth_headers, db_session, monkeypatch
):
    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    created = _create_token(client, auth_headers, ["workers:register"])
    client.cookies.clear()

    response = client.post(
        "/api/v2/workers/heartbeat",
        json=_heartbeat("worker-scoped-token"),
        headers={"Authorization": f"Bearer {created['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ONLINE"
    token = db_session.get(ApiToken, created["id"])
    assert token is not None
    assert token.last_used_at is not None


def test_ci_trigger_token_cannot_register_worker(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    created = _create_token(client, auth_headers, ["trigger"])
    client.cookies.clear()

    response = client.post(
        "/api/v2/workers/heartbeat",
        json=_heartbeat("worker-wrong-scope"),
        headers={"Authorization": f"Bearer {created['token']}"},
    )

    assert response.status_code == 403
    assert "workers:register" in response.json()["msg"]


def test_disabled_worker_token_is_rejected(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    created = _create_token(client, auth_headers, ["workers:register"])
    disabled = client.put(
        f"/api/v1/tokens/{created['id']}",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert disabled.status_code == 200
    client.cookies.clear()

    response = client.post(
        "/api/v2/workers/heartbeat",
        json=_heartbeat("worker-disabled-token"),
        headers={"Authorization": f"Bearer {created['token']}"},
    )

    assert response.status_code == 401
    assert "已禁用" in response.json()["msg"]
