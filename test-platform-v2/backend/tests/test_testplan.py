"""Test plan module tests — CRUD lifecycle + execution."""
from __future__ import annotations


class TestPlanCRUD:
    """测试计划创建/查询/更新/删除"""

    def test_create_plan(self, client, auth_headers):
        resp = client.post("/api/v1/test-plans", json={
            "name": "回归测试计划 v1.0",
            "description": "冒烟+全量回归",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "回归测试计划 v1.0"
        assert data["id"] > 0

    def test_list_plans(self, client, auth_headers):
        # Create two plans
        for name in ["计划A", "计划B"]:
            client.post("/api/v1/test-plans", json={"name": name}, headers=auth_headers)
        resp = client.get("/api/v1/test-plans", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) >= 2

    def test_get_plan_detail(self, client, auth_headers):
        # Create a plan first
        r = client.post("/api/v1/test-plans", json={"name": "详情测试计划"}, headers=auth_headers)
        plan_id = r.json()["data"]["id"]
        resp = client.get(f"/api/v1/test-plans/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "详情测试计划"

    def test_update_plan(self, client, auth_headers):
        r = client.post("/api/v1/test-plans", json={"name": "旧名称"}, headers=auth_headers)
        plan_id = r.json()["data"]["id"]
        resp = client.put(f"/api/v1/test-plans/{plan_id}", json={
            "name": "新名称", "description": "更新后的描述",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名称"

    def test_delete_plan(self, client, auth_headers):
        r = client.post("/api/v1/test-plans", json={"name": "待删除计划"}, headers=auth_headers)
        plan_id = r.json()["data"]["id"]
        resp = client.delete(f"/api/v1/test-plans/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200
        # Verify deleted
        resp2 = client.get(f"/api/v1/test-plans/{plan_id}", headers=auth_headers)
        assert resp2.status_code == 404


class TestPlanAuthorization:
    """测试计划权限校验"""

    def test_no_token_rejected(self, client):
        resp = client.get("/api/v1/test-plans")
        assert resp.status_code == 401

    def test_list_by_status_filter(self, client, auth_headers):
        resp = client.get("/api/v1/test-plans?status=draft", headers=auth_headers)
        assert resp.status_code == 200


class TestPlanExecution:
    """测试计划执行"""

    def test_execute_empty_plan(self, client, auth_headers):
        """空计划（无关联用例）执行应正常返回。"""
        r = client.post("/api/v1/test-plans", json={"name": "空计划"}, headers=auth_headers)
        plan_id = r.json()["data"]["id"]
        # Trigger execution (may succeed or return a reasonable error for empty plan)
        resp = client.post(f"/api/v1/test-plans/{plan_id}/execute", headers=auth_headers)
        # Accept 200 (success) or 400 (validation error)
        assert resp.status_code in (200, 400)
