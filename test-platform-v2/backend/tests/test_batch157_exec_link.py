"""Batch 157：执行模型双向关联（test_execution ↔ api_execution_task）。"""
from __future__ import annotations


def _create_api_case(client, auth_headers, *, endpoint="/api/ping", title="B157TMP-API用例"):
    resp = client.post("/api/v1/test-cases", json={
        "title": title,
        "case_type": "api",
        "api_method": "GET",
        "api_endpoint": endpoint,
        "api_headers": "{}",
        "api_assertions": '[{"type": "status_code", "op": "eq", "expected": 200}]',
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _create_environment(client, auth_headers, *, base_url="http://127.0.0.1:1"):
    resp = client.post("/api/v1/environments", json={
        "name": "B157TMP-环境", "env_type": "test", "base_url": base_url,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _create_plan_with_case(client, auth_headers, case_id, name="B157TMP-计划"):
    plan = client.post("/api/v1/test-plans", json={"name": name}, headers=auth_headers).json()["data"]
    add = client.post(
        f"/api/v1/test-plans/{plan['id']}/cases",
        json={"case_ids": [case_id]},
        headers=auth_headers,
    )
    assert add.status_code == 200
    assert add.json()["data"]["added"] == 1
    return plan


class TestExecutionModelLink:
    """Batch 157：计划 API 执行 → trigger_type=plan 任务 + 双向关联。"""

    def test_execute_all_creates_linked_api_task(self, client, auth_headers):
        case_id = _create_api_case(client, auth_headers)
        env_id = _create_environment(client, auth_headers)
        plan = _create_plan_with_case(client, auth_headers, case_id, "B157TMP-批量关联")

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/execute-all",
            json={"environment_id": env_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["code"] == 0, resp.json()

        execs = client.get(f"/api/v1/test-plans/{plan['id']}/executions", headers=auth_headers).json()["data"]["items"]
        api_exec = next(e for e in execs if e["case_id"] == case_id)
        assert api_exec["api_task_id"] is not None

        tasks = client.get("/api/v1/apitest/tasks", params={"page_size": 50}, headers=auth_headers).json()["data"]["items"]
        plan_task = next(t for t in tasks if t["trigger_type"] == "plan")
        assert plan_task["status"] == "success"
        assert plan_task["passed"] + plan_task["failed"] == plan_task["total"] == 1

        detail = client.get(f"/api/v1/apitest/tasks/{plan_task['id']}", headers=auth_headers).json()["data"]
        linked = [it for it in detail["items"] if it["test_execution_id"] == api_exec["id"]]
        assert len(linked) == 1

    def test_auto_execute_creates_linked_api_task(self, client, auth_headers):
        case_id = _create_api_case(client, auth_headers)
        env_id = _create_environment(client, auth_headers)
        plan = _create_plan_with_case(client, auth_headers, case_id, "B157TMP-自动关联")

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/auto-execute",
            json={"environment_id": env_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["code"] == 0, resp.json()

        execs = client.get(f"/api/v1/test-plans/{plan['id']}/executions", headers=auth_headers).json()["data"]["items"]
        api_exec = next(e for e in execs if e["case_id"] == case_id)
        assert api_exec["api_task_id"] is not None

        tasks = client.get("/api/v1/apitest/tasks", params={"page_size": 50}, headers=auth_headers).json()["data"]["items"]
        plan_task = next(t for t in tasks if t["trigger_type"] == "plan")
        detail = client.get(f"/api/v1/apitest/tasks/{plan_task['id']}", headers=auth_headers).json()["data"]
        assert any(it["test_execution_id"] == api_exec["id"] for it in detail["items"])

    def test_apitest_independent_task_has_no_link(self, db_session, client, auth_headers):
        """独立接口测试任务不产生 test_execution_id（保持独立语义）。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

        case_id = _create_api_case(client, auth_headers)
        task = ApiExecutionTask(project_id=1, task_id="B157TMP-独立", name="B157TMP-独立任务", total=1)
        db_session.add(task)
        db_session.flush()
        db_session.add(ApiExecutionTaskItem(task_id=task.id, case_id=case_id))
        db_session.commit()

        detail = client.get(f"/api/v1/apitest/tasks/{task.id}", headers=auth_headers).json()["data"]
        assert len(detail["items"]) == 1
        assert detail["items"][0]["test_execution_id"] is None
