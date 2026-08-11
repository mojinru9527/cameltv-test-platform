"""Batch 148 P0 修复回归：缺陷契约 + 执行预检 + 失败根因字段。"""
from __future__ import annotations

import json


def _create_api_case(client, auth_headers, *, endpoint="/api/ping", headers="{}", title="B148TMP-API用例", assertions='[{"type": "status_code", "op": "eq", "expected": 200}]'):
    resp = client.post("/api/v1/test-cases", json={
        "title": title,
        "case_type": "api",
        "api_method": "GET",
        "api_endpoint": endpoint,
        "api_headers": headers,
        "api_assertions": assertions,
    }, headers=auth_headers)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_plan_with_case(client, auth_headers, case_id, name="B148TMP-计划"):
    plan = client.post("/api/v1/test-plans", json={"name": name}, headers=auth_headers).json()["data"]
    add = client.post(
        f"/api/v1/test-plans/{plan['id']}/cases",
        json={"case_ids": [case_id]},
        headers=auth_headers,
    )
    assert add.status_code == 200
    assert add.json()["data"]["added"] == 1
    return plan


def _create_environment(client, auth_headers, *, name="B148TMP-环境", base_url="http://127.0.0.1:1"):
    resp = client.post("/api/v1/environments", json={
        "name": name, "env_type": "test", "base_url": base_url,
    }, headers=auth_headers)
    assert resp.status_code == 200
    return resp.json()["data"]


class TestDefectContract:
    """P0-01：缺陷创建 assignee_id Optional 契约。"""

    def test_create_defect_without_assignee(self, client, auth_headers):
        resp = client.post("/api/v1/defects", json={
            "title": "B148TMP-缺陷契约-不选处理人",
            "description": "assignee_id 缺省",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] > 0
        assert data["assignee_id"] == 0

    def test_create_defect_with_null_assignee(self, client, auth_headers):
        resp = client.post("/api/v1/defects", json={
            "title": "B148TMP-缺陷契约-null处理人",
            "assignee_id": None,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["assignee_id"] == 0


class TestExecutionPrecheck:
    """P0-02：执行前环境/Token 就绪检查。"""

    def test_execute_all_blocked_without_environment(self, client, auth_headers):
        case_id = _create_api_case(client, auth_headers)
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-无环境计划")

        resp = client.post(f"/api/v1/test-plans/{plan['id']}/execute-all", json={}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] != 0
        assert "执行环境" in resp.json()["msg"]

        execs = client.get(f"/api/v1/test-plans/{plan['id']}/executions", headers=auth_headers).json()["data"]
        assert execs["total"] == 0

    def test_auto_execute_blocked_without_environment(self, client, auth_headers):
        case_id = _create_api_case(client, auth_headers)
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-无环境自动执行")

        resp = client.post(f"/api/v1/test-plans/{plan['id']}/auto-execute", json={}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] != 0
        assert "执行环境" in resp.json()["msg"]

    def test_execute_all_blocked_missing_base_url(self, client, auth_headers):
        case_id = _create_api_case(client, auth_headers, endpoint="/api/ping")
        env = _create_environment(client, auth_headers, base_url="")
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-无base_url")

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/execute-all",
            json={"environment_id": env["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] != 0
        assert "base_url" in resp.json()["msg"]

    def test_execute_all_blocked_missing_token_variable(self, client, auth_headers):
        case_id = _create_api_case(
            client, auth_headers,
            headers=json.dumps({"Authorization": "${token}"}),
        )
        env = _create_environment(client, auth_headers)  # 无 token 变量
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-缺token")

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/execute-all",
            json={"environment_id": env["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] != 0
        assert "token" in resp.json()["msg"]


class TestExecutionErrorFields:
    """P0-02：执行记录失败根因独立字段 + 历史 JSON 回填。"""

    def test_execute_all_records_error_fields(self, client, auth_headers):
        # 127.0.0.1 被 SSRF 拦截 → TARGET_POLICY 错误，确定性且快速
        case_id = _create_api_case(client, auth_headers, endpoint="/x")
        env = _create_environment(client, auth_headers, base_url="http://127.0.0.1:1")
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-失败字段")

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/execute-all",
            json={"environment_id": env["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["failed"] == 1

        execs = client.get(f"/api/v1/test-plans/{plan['id']}/executions", headers=auth_headers).json()["data"]
        assert execs["total"] == 1
        item = execs["items"][0]
        assert item["status"] == "fail"
        assert item["error_type"] in ("TARGET_POLICY", "NETWORK_ERROR")
        assert item["status_code"] == 0
        assert item["error_message"]

    def test_execution_history_backfills_error_fields_from_json(self, client, auth_headers):
        """历史行只有 actual_result JSON 时，读取应回填三字段。"""
        case_id = _create_api_case(client, auth_headers)
        plan = _create_plan_with_case(client, auth_headers, case_id, "B148TMP-历史回填")
        detail = client.get(f"/api/v1/test-plans/{plan['id']}", headers=auth_headers).json()["data"]
        pcase = detail["cases"][0]

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/cases/{pcase['id']}/execute",
            json={
                "status": "fail",
                "actual_result": json.dumps({
                    "error": "连接失败: 无法解析主机",
                    "error_type": "NETWORK_ERROR",
                    "status_code": 0,
                }, ensure_ascii=False),
                "notes": "历史数据（无独立字段）",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        execs = client.get(f"/api/v1/test-plans/{plan['id']}/executions", headers=auth_headers).json()["data"]
        item = execs["items"][0]
        assert item["error_type"] == "NETWORK_ERROR"
        assert item["error_message"] == "连接失败: 无法解析主机"
        assert item["status_code"] == 0
