"""Batch 157/186：执行模型关联语义。

Batch 157 曾建立 test_execution ↔ api_execution_task 双向关联（计划执行双写）；
Batch 186（C182-1）确立唯一事实源 = test_execution：计划执行不再创建
trigger_type=plan 任务/items、不再写 api_task_id；独立接口测试任务保持独立语义。
"""
from __future__ import annotations


def _create_api_case(
    client, auth_headers, *, endpoint="/api/ping", title="B157TMP-API用例"
):
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


def _create_environment(
    client, auth_headers, *, base_url="http://127.0.0.1:1"
):
    resp = client.post("/api/v1/environments", json={
        "name": "B157TMP-环境", "env_type": "test", "base_url": base_url,
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _create_plan_with_case(client, auth_headers, case_id, name="B157TMP-计划"):
    plan = client.post(
        "/api/v1/test-plans", json={"name": name}, headers=auth_headers
    ).json()["data"]
    add = client.post(
        f"/api/v1/test-plans/{plan['id']}/cases",
        json={"case_ids": [case_id]},
        headers=auth_headers,
    )
    assert add.status_code == 200
    assert add.json()["data"]["added"] == 1
    return plan


class TestExecutionModelLink:
    """Batch 186（C182-1）：计划执行唯一事实源 = test_execution。"""

    def test_execute_all_creates_only_test_execution(self, client, auth_headers):
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

        execs = client.get(
            f"/api/v1/test-plans/{plan['id']}/executions",
            headers=auth_headers,
        ).json()["data"]["items"]
        api_exec = next(e for e in execs if e["case_id"] == case_id)
        # C182-1：不再与 plan 任务互指（api_task_id 保持 NULL）
        assert api_exec["api_task_id"] is None

        tasks = client.get(
            "/api/v1/apitest/tasks",
            params={"page_size": 50},
            headers=auth_headers,
        ).json()["data"]["items"]
        # C182-1：计划执行不再创建 trigger_type=plan 任务
        assert not any(t["trigger_type"] == "plan" for t in tasks)

    def test_auto_execute_creates_only_test_execution(self, client, auth_headers):
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

        execs = client.get(
            f"/api/v1/test-plans/{plan['id']}/executions",
            headers=auth_headers,
        ).json()["data"]["items"]
        api_exec = next(e for e in execs if e["case_id"] == case_id)
        assert api_exec["api_task_id"] is None

        tasks = client.get(
            "/api/v1/apitest/tasks",
            params={"page_size": 50},
            headers=auth_headers,
        ).json()["data"]["items"]
        assert not any(t["trigger_type"] == "plan" for t in tasks)

    def test_apitest_independent_task_has_no_link(
        self, db_session, client, auth_headers
    ):
        """独立接口测试任务不产生 test_execution_id（保持独立语义）。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

        case_id = _create_api_case(client, auth_headers)
        task = ApiExecutionTask(
            project_id=1, task_id="B157TMP-独立",
            name="B157TMP-独立任务", total=1,
        )
        db_session.add(task)
        db_session.flush()
        db_session.add(ApiExecutionTaskItem(task_id=task.id, case_id=case_id))
        db_session.commit()

        detail = client.get(
            f"/api/v1/apitest/tasks/{task.id}", headers=auth_headers
        ).json()["data"]
        assert len(detail["items"]) == 1
        assert detail["items"][0]["test_execution_id"] is None
