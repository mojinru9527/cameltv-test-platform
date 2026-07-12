"""切片 4 —— Wiki API 层：配置读取 + 权限/开关门禁（HTTP）。

主链路(导入→编译→差异→产物)的业务逻辑由 *_in_new_session 后台函数承载，已在
test_wiki_ingest / test_wiki_diff 以组件级(db_session)覆盖；此处只校验 API 接线、
RBAC 与配置开关门禁。
"""
from __future__ import annotations

import pytest

from app.core.config import settings


@pytest.fixture()
def wiki_off(monkeypatch):
    monkeypatch.setattr(settings, "wiki_enabled", False, raising=False)
    monkeypatch.setattr(settings, "wiki_diff_enabled", False, raising=False)


def test_config_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "wiki_enabled", True, raising=False)
    r = client.get("/api/v1/wiki/config", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["wiki_enabled"] is True and "lanhu_mcp_enabled" in data


def test_import_gated_when_wiki_off(client, auth_headers, wiki_off):
    r = client.post("/api/v1/wiki/import/lanhu", headers=auth_headers,
                    json={"url": "https://lanhuapp.com/x?docId=a&pageId=b"})
    assert r.status_code == 503
    assert "未启用" in r.json()["msg"]


def test_diff_gated_when_diff_off(client, auth_headers, wiki_off):
    r = client.post("/api/v1/wiki/diff/tasks", headers=auth_headers,
                    json={"query": "比赛推送"})
    assert r.status_code == 503


def test_raw_sources_list_empty(client, auth_headers):
    r = client.get("/api/v1/wiki/raw-sources", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 0


def test_requires_auth(client):
    r = client.get("/api/v1/wiki/config")
    assert r.status_code in (401, 403)
