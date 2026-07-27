"""VNext-5: 外部 LLM-Wiki 连接器测试。

覆盖：
- 401 未认证
- 503 开关关闭
- 超时处理
- 成功健康检查（mock httpx）
- 项目隔离
- CRUD 流程
"""
from __future__ import annotations

import pytest

from app.core.config import settings


# ── helpers ──

@pytest.fixture()
def external_off(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_wiki_enabled", False, raising=False)


@pytest.fixture()
def external_on(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_wiki_enabled", True, raising=False)


# ── 401 / authentication ──

def test_requires_auth_external(client):
    """外部连接端点需要认证。"""
    r = client.get("/api/v1/wiki/external-connections")
    assert r.status_code in (401, 403)


def test_requires_auth_external_create(client):
    r = client.post("/api/v1/wiki/external-connections", json={
        "name": "Test", "base_url": "http://localhost:9999",
    })
    assert r.status_code in (401, 403)


# ── 503 / config gate ──

def test_list_gated_when_off(client, auth_headers, external_off):
    r = client.get("/api/v1/wiki/external-connections", headers=auth_headers)
    assert r.status_code == 503
    assert "未启用" in r.json()["msg"]


def test_create_gated_when_off(client, auth_headers, external_off):
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Test", "base_url": "http://localhost:9999",
    })
    assert r.status_code == 503


def test_health_check_gated_when_off(client, auth_headers, external_off):
    r = client.post("/api/v1/wiki/external-connections/1/health-check", headers=auth_headers)
    assert r.status_code == 503


def test_search_gated_when_off(client, auth_headers, external_off):
    r = client.post("/api/v1/wiki/external-connections/1/search", headers=auth_headers,
                    json={"query": "test"})
    assert r.status_code == 503


# ── CRUD flow ──

def test_create_and_list_connection(client, auth_headers, external_on, db_session):
    """创建连接 → 列表中可见，且 token 不暴露。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "My Wiki",
        "provider": "llm_wiki_desktop",
        "base_url": "http://localhost:9999/",
        "token": "secret-token-123",
        "external_project_id": "ext-proj-1",
        "enabled": True,
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "My Wiki"
    assert data["provider"] == "llm_wiki_desktop"
    assert data["base_url"] == "http://localhost:9999"
    assert data["external_project_id"] == "ext-proj-1"
    assert data["enabled"] is True
    # token 绝不暴露
    assert "token_encrypted" not in data
    assert "secret-token-123" not in r.text
    conn_id = data["id"]

    r = client.get("/api/v1/wiki/external-connections", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()["data"]
    assert any(c["id"] == conn_id for c in items)


def test_get_connection_detail(client, auth_headers, external_on, db_session):
    """获取单个连接详情。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Detail Test", "base_url": "http://localhost:9998",
    })
    conn_id = r.json()["data"]["id"]

    r = client.get(f"/api/v1/wiki/external-connections/{conn_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Detail Test"


def test_update_connection(client, auth_headers, external_on, db_session):
    """更新连接配置：名称/URL/token 均可更新。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Old Name", "base_url": "http://old:9999", "token": "old-token",
    })
    conn_id = r.json()["data"]["id"]

    r = client.put(f"/api/v1/wiki/external-connections/{conn_id}", headers=auth_headers, json={
        "name": "New Name",
        "base_url": "http://new:9999",
        "token": "new-token",
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "New Name"
    assert data["base_url"] == "http://new:9999"


def test_update_connection_empty_token_not_changed(client, auth_headers, external_on, db_session):
    """token 传空字符串时不覆盖已有 token。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Token Test", "base_url": "http://localhost:9997", "token": "keep-me",
    })
    conn_id = r.json()["data"]["id"]

    r = client.put(f"/api/v1/wiki/external-connections/{conn_id}", headers=auth_headers, json={
        "name": "Token Test Updated",
    })
    assert r.status_code == 200
    # token 应保持不变；健康检查应能解密成功（不抛异常即成功）
    r = client.post(f"/api/v1/wiki/external-connections/{conn_id}/health-check",
                    headers=auth_headers)
    # 连不上是预期行为（mock server 未启动），但不应解密失败
    assert r.status_code == 200
    data = r.json()["data"]
    assert "ok" in data  # ok=False 因为连不上，但不是 500


def test_delete_connection(client, auth_headers, external_on, db_session):
    """删除连接后 404。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "To Delete", "base_url": "http://localhost:9996",
    })
    conn_id = r.json()["data"]["id"]

    r = client.delete(f"/api/v1/wiki/external-connections/{conn_id}", headers=auth_headers)
    assert r.status_code == 200

    r = client.get(f"/api/v1/wiki/external-connections/{conn_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["code"] == 404


# ── project isolation ──

def test_cannot_access_other_project_connection(client, auth_headers, external_on, db_session):
    """创建连接后，另一个项目无法访问。"""
    # 当前项目 project_id=1（由 auth_headers fixture 注入 X-Project-Id: 1）
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Project 1 Conn", "base_url": "http://p1:9999",
    })
    conn_id = r.json()["data"]["id"]

    # 切换到 project_id=2 的 headers
    headers_p2 = dict(auth_headers)
    headers_p2["X-Project-Id"] = "2"
    r = client.get(f"/api/v1/wiki/external-connections/{conn_id}", headers=headers_p2)
    assert r.status_code == 200
    assert r.json()["code"] == 404  # 项目隔离，找不到

    r = client.get("/api/v1/wiki/external-connections", headers=headers_p2)
    assert r.status_code == 200
    assert len(r.json()["data"]) == 0  # 项目2看不到项目1的连接


# ── health check ──

def test_health_check_fails_when_base_url_unreachable(client, auth_headers, external_on, db_session):
    """连接不可达时返回 ok=False 而不是 500。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Unreachable", "base_url": "http://127.0.0.1:19999",
    })
    conn_id = r.json()["data"]["id"]

    r = client.post(f"/api/v1/wiki/external-connections/{conn_id}/health-check",
                    headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["ok"] is False
    assert data["message"]  # 有错误描述


# ── search / read / graph with unreachable connection ──

def test_search_returns_empty_on_failure(client, auth_headers, external_on, db_session):
    """不可达连接搜索返回空列表，不抛 500。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Search Test", "base_url": "http://127.0.0.1:19998",
    })
    conn_id = r.json()["data"]["id"]

    r = client.post(f"/api/v1/wiki/external-connections/{conn_id}/search",
                    headers=auth_headers, json={"query": "比赛"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "items" in data


def test_read_page_returns_error_on_failure(client, auth_headers, external_on, db_session):
    """不可达连接读取页面返回 ok=False。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Read Test", "base_url": "http://127.0.0.1:19997",
    })
    conn_id = r.json()["data"]["id"]

    r = client.get(f"/api/v1/wiki/external-connections/{conn_id}/files/content?path=index",
                   headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["ok"] is False


def test_graph_returns_error_on_failure(client, auth_headers, external_on, db_session):
    """不可达连接获取图谱返回 ok=False。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "Graph Test", "base_url": "http://127.0.0.1:19996",
    })
    conn_id = r.json()["data"]["id"]

    r = client.get(f"/api/v1/wiki/external-connections/{conn_id}/graph?node=match_push",
                   headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["ok"] is False


# ── 404 for non-existent connection ──

def test_404_for_nonexistent_connection(client, auth_headers, external_on):
    """不存在的连接返回 404。"""
    r = client.get("/api/v1/wiki/external-connections/99999", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["code"] == 404


# ── validation ──

def test_create_requires_base_url(client, auth_headers, external_on):
    """创建连接时 base_url 必填。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "name": "No URL",
    })
    assert r.status_code == 422


def test_create_requires_name(client, auth_headers, external_on):
    """创建连接时 name 必填。"""
    r = client.post("/api/v1/wiki/external-connections", headers=auth_headers, json={
        "base_url": "http://localhost:9999",
    })
    assert r.status_code == 422


# ── service-level timeout handling ──

def test_service_health_check_timeout_handling(monkeypatch):
    """服务层健康检查在超时后不抛异常，返回 ok=False。"""
    from app.services.wiki.external_llm_wiki import health_check as svc_health_check

    class FakeConn:
        id = 1
        base_url = "http://10.255.255.1:1"  # non-routable IP → 超时
        provider = "llm_wiki_desktop"
        token_encrypted = None
        external_project_id = None

    # 将httpx默认超时降到极小值，加速测试
    import httpx
    original_client = httpx.Client

    class FastTimeoutClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("timeout", 0.5)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.services.wiki.external_llm_wiki.httpx.Client", FastTimeoutClient)
    result = svc_health_check(FakeConn)
    assert result["ok"] is False
    assert result["message"]  # 有错误描述


def test_service_search_timeout_returns_empty(monkeypatch):
    """服务层搜索超时返回空列表。"""
    from app.services.wiki.external_llm_wiki import search as svc_search

    class FakeConn:
        id = 1
        base_url = "http://10.255.255.1:1"
        provider = "llm_wiki_desktop"
        token_encrypted = None
        external_project_id = None

    import httpx

    class FastTimeoutClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("timeout", 0.5)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.services.wiki.external_llm_wiki.httpx.Client", FastTimeoutClient)
    result = svc_search(FakeConn, "test query", limit=5)
    assert result == []


# ── successful health check (with httpx mock) ──

def test_service_health_check_success(monkeypatch):
    """Mock httpx 验证成功健康检查路径。"""
    from app.services.wiki.external_llm_wiki import health_check as svc_health_check

    class FakeConn:
        id = 1
        base_url = "http://fake-wiki.local"
        provider = "llm_wiki_desktop"
        token_encrypted = None
        external_project_id = None

    class FakeResponse:
        status_code = 200
        is_success = True

        @staticmethod
        def json():
            return {"version": "2.3.1", "status": "ok"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, method, url, headers=None, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.wiki.external_llm_wiki.httpx.Client", FakeClient)
    result = svc_health_check(FakeConn)
    assert result["ok"] is True
    assert result["version"] == "2.3.1"
    assert result["message"] == "连接正常"
