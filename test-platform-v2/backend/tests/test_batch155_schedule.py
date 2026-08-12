"""Batch 155：P2-15/18 报告定时生成 + 调度停用原因。"""
from __future__ import annotations


def _create_plan(client, auth_headers, name="B155TMP-调度计划"):
    resp = client.post("/api/v1/test-plans", json={"name": name}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestScheduleReportAndDisabledReason:
    """P2-15/18：job_type=report 定时生成 + disabled_reason 必填。"""

    def test_create_report_schedule(self, client, auth_headers):
        plan = _create_plan(client, auth_headers)
        resp = client.post("/api/v1/schedules", json={
            "name": "B155TMP-报告定时",
            "job_type": "report",
            "plan_id": plan["id"],
            "cron_expression": "0 2 * * *",
            "enabled": False,
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["job_type"] == "report"
        assert data["disabled_reason"] == ""

    def test_disable_requires_reason(self, client, auth_headers):
        plan = _create_plan(client, auth_headers, "B155TMP-停用原因")
        sched = client.post("/api/v1/schedules", json={
            "name": "B155TMP-停用测试",
            "job_type": "plan",
            "plan_id": plan["id"],
            "cron_expression": "0 3 * * *",
        }, headers=auth_headers).json()["data"]

        resp = client.put(f"/api/v1/schedules/{sched['id']}", json={"enabled": False}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] != 0
        assert "停用原因" in resp.json()["msg"]

        resp2 = client.put(
            f"/api/v1/schedules/{sched['id']}",
            json={"enabled": False, "disabled_reason": "B155TMP-计划暂停"},
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["code"] == 0
        assert resp2.json()["data"]["enabled"] is False
        assert resp2.json()["data"]["disabled_reason"] == "B155TMP-计划暂停"

        # 重新启用后清空原因
        resp3 = client.put(f"/api/v1/schedules/{sched['id']}", json={"enabled": True}, headers=auth_headers)
        assert resp3.json()["data"]["disabled_reason"] == ""

    def test_invalid_job_type_rejected(self, client, auth_headers):
        plan = _create_plan(client, auth_headers, "B155TMP-非法类型")
        resp = client.post("/api/v1/schedules", json={
            "name": "B155TMP-非法",
            "job_type": "perf",
            "plan_id": plan["id"],
            "cron_expression": "0 4 * * *",
        }, headers=auth_headers)
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.json()["code"] != 0

