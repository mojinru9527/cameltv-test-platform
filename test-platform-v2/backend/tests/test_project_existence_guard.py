"""Reject nonexistent project scopes before domain handlers can read or mutate data."""
from __future__ import annotations

import pytest

from app.models.knowledge import AgentQueueItem
from app.models.notification import NotificationChannel


INVALID_PROJECT_ID = 999999


def _invalid_project_headers(auth_headers: dict) -> dict:
    return {**auth_headers, "X-Project-Id": str(INVALID_PROJECT_ID)}


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("get", "/api/v1/knowledge/sources", None),
        ("get", "/api/v1/notify/channels", None),
        ("get", "/api/v1/agents/runs", None),
        ("get", "/api/v1/agents/types", None),
        ("post", "/api/v1/knowledge/search", {"query": "private project data"}),
    ],
)
def test_nonexistent_project_reads_are_rejected_without_domain_payload(
    client,
    auth_headers,
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    response = client.request(
        method,
        path,
        headers=_invalid_project_headers(auth_headers),
        json=json_body,
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "项目不存在", "data": None}
    assert "items" not in response.text
    assert "total" not in response.text
    assert "private project data" not in response.text


def test_nonexistent_project_notification_write_has_no_side_effect(
    client,
    auth_headers,
    db_session,
) -> None:
    before = db_session.query(NotificationChannel).count()

    response = client.post(
        "/api/v1/notify/channels",
        headers=_invalid_project_headers(auth_headers),
        json={
            "name": "must-not-persist",
            "channel_type": "webhook",
            "provider": "generic",
            "webhook_url": "https://example.invalid/hook",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "项目不存在", "data": None}
    assert db_session.query(NotificationChannel).count() == before


def test_nonexistent_project_agent_trigger_has_no_side_effect(
    client,
    auth_headers,
    db_session,
) -> None:
    before = db_session.query(AgentQueueItem).count()

    response = client.post(
        "/api/v1/agents/run/requirement_analysis",
        headers=_invalid_project_headers(auth_headers),
        json={"query": "must-not-queue"},
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "项目不存在", "data": None}
    assert db_session.query(AgentQueueItem).count() == before
