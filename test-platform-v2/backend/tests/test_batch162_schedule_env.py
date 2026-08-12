"""Batch 162 / C161-2 — 调度绑定执行环境回归测试。"""
from __future__ import annotations


def _create_env(client, auth_headers, name="B162TMP-环境"):
    resp = client.post("/api/v1/environments", json={
        "name": name, "env_type": "test", "base_url": "https://example.com",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _create_case(client, auth_headers, case_type="api"):
    body = {"title": "B162TMP-用例", "case_type": case_type}
    if case_type == "api":
        body.update({"api_method": "GET", "api_endpoint": "/ping", "domain": "接口测试/首页", "module": "探活"})
    resp = client.post("/api/v1/test-cases", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _create_plan(client, auth_headers, case_id):
    resp = client.post("/api/v1/test-plans", json={"name": "B162TMP-计划"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    plan = resp.json()["data"]
    add = client.post(f"/api/v1/test-plans/{plan['id']}/cases", json={"case_ids": [case_id]}, headers=auth_headers)
    assert add.status_code == 200, add.text
    return plan


def _schedule_payload(plan_id, environment_id=None):
    payload = {
        "name": "B162TMP-调度",
        "plan_id": plan_id,
        "job_type": "plan",
        "cron_expression": "0 4 * * *",
        "enabled": False,
        "description": "batch-162 test",
    }
    if environment_id is not None:
        payload["environment_id"] = environment_id
    return payload


class TestBatch162ScheduleEnv:
    def test_api_plan_requires_env(self, client, auth_headers):
        case = _create_case(client, auth_headers, case_type="api")
        plan = _create_plan(client, auth_headers, case["id"])
        resp = client.post("/api/v1/schedules", json=_schedule_payload(plan["id"]), headers=auth_headers)
        body = resp.json()
        assert body.get("code") != 0 or resp.status_code >= 400, resp.text
        assert "执行环境" in (body.get("msg") or "")

    def test_api_plan_with_env_ok(self, client, auth_headers):
        env = _create_env(client, auth_headers)
        case = _create_case(client, auth_headers, case_type="api")
        plan = _create_plan(client, auth_headers, case["id"])
        resp = client.post("/api/v1/schedules", json=_schedule_payload(plan["id"], env["id"]), headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["environment_id"] == env["id"]
        # 更新为其它环境
        env2 = _create_env(client, auth_headers, name="B162TMP-环境2")
        upd = client.put(f"/api/v1/schedules/{data['id']}", json={"environment_id": env2["id"]}, headers=auth_headers)
        assert upd.status_code == 200, upd.text
        assert upd.json()["data"]["environment_id"] == env2["id"]
        # API 计划显式清空环境应被拦截
        upd2 = client.put(f"/api/v1/schedules/{data['id']}", json={"environment_id": None}, headers=auth_headers)
        body2 = upd2.json()
        assert body2.get("code") != 0 or upd2.status_code >= 400, upd2.text
        assert "执行环境" in (body2.get("msg") or "")

    def test_manual_plan_without_env_ok(self, client, auth_headers):
        case = _create_case(client, auth_headers, case_type="manual")
        plan = _create_plan(client, auth_headers, case["id"])
        resp = client.post("/api/v1/schedules", json=_schedule_payload(plan["id"]), headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["environment_id"] is None
