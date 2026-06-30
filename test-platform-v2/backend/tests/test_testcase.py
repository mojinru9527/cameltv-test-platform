"""Test case CRUD tests — create, read, update, delete, domain tree."""
from __future__ import annotations


class TestCaseCRUD:
    def test_create_case(self, client, auth_headers):
        resp = client.post("/api/v1/test-cases", json={
            "title": "登录功能-正常登录", "domain": "用户端",
            "module": "登录", "priority": "P0", "case_type": "manual",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "登录功能-正常登录"
        assert data["priority"] == "P0"
        assert data["id"] > 0

    def test_list_cases(self, client, auth_headers):
        # Create 2 cases
        for i in range(2):
            client.post("/api/v1/test-cases", json={
                "title": f"Case {i}", "domain": "用户端",
                "module": "测试", "priority": "P1",
            }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_get_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Detail test", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.get(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Detail test"

    def test_update_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Old title", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.put(f"/api/v1/test-cases/{case_id}", json={
            "title": "New title", "priority": "P2",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New title"

    def test_delete_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Delete me", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        # Verify deleted
        get_resp = client.get(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["code"] == 404

    def test_filter_by_domain(self, client, auth_headers):
        client.post("/api/v1/test-cases", json={
            "title": "Case A", "domain": "用户端", "module": "登录",
        }, headers=auth_headers)
        client.post("/api/v1/test-cases", json={
            "title": "Case B", "domain": "运营后台", "module": "配置",
        }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases?domain=用户端", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(item["domain"] == "用户端" for item in data["items"])

    def test_domain_tree(self, client, auth_headers):
        client.post("/api/v1/test-cases", json={
            "title": "Tree test", "domain": "用户端", "module": "登录",
        }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases/domains", headers=auth_headers)
        assert resp.status_code == 200
        domains = resp.json()["data"]
        assert len(domains) > 0
        assert any(d["domain"] == "用户端" for d in domains)


class TestCaseBatch:
    def test_batch_update(self, client, auth_headers):
        ids = []
        for i in range(3):
            r = client.post("/api/v1/test-cases", json={
                "title": f"Batch {i}", "domain": "用户端", "module": "测试",
                "priority": "P3",
            }, headers=auth_headers)
            ids.append(r.json()["data"]["id"])

        resp = client.put("/api/v1/test-cases/batch", json={
            "ids": ids, "priority": "P0",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["updated"] == 3

        # Verify all updated
        for cid in ids:
            r = client.get(f"/api/v1/test-cases/{cid}", headers=auth_headers)
            assert r.json()["data"]["priority"] == "P0"

    def test_batch_delete(self, client, auth_headers):
        ids = []
        for i in range(2):
            r = client.post("/api/v1/test-cases", json={
                "title": f"Del batch {i}", "domain": "用户端", "module": "测试",
            }, headers=auth_headers)
            ids.append(r.json()["data"]["id"])

        resp = client.delete("/api/v1/test-cases/batch", json={
            "ids": ids,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2
