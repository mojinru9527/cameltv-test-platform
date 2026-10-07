"""Reject nonexistent project scopes before domain handlers can read or mutate data.

平台简化批次：通知/Agent 域已删除，仅保留项目知识域的守卫契约。
"""
from __future__ import annotations

import pytest


INVALID_PROJECT_ID = 999999


def _invalid_project_headers(auth_headers: dict) -> dict:
    return {**auth_headers, "X-Project-Id": str(INVALID_PROJECT_ID)}


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("get", "/api/v1/knowledge/sources", None),
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
