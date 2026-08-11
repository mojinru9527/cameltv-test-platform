"""Batch 149 统计口径收敛回归：dashboard/trace/plan-list 数字一致 + is_deleted 过滤。"""
from __future__ import annotations


def _create_case(client, auth_headers, *, title="B149TMP-用例", case_type="manual", endpoint=""):
    resp = client.post("/api/v1/test-cases", json={
        "title": title,
        "case_type": case_type,
        "api_method": "GET" if case_type == "api" else "",
        "api_endpoint": endpoint,
    }, headers=auth_headers)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_plan(client, auth_headers, name="B149TMP-计划", status="active"):
    resp = client.post("/api/v1/test-plans", json={"name": name, "status": status}, headers=auth_headers)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _add_cases(client, auth_headers, plan_id, case_ids):
    resp = client.post(
        f"/api/v1/test-plans/{plan_id}/cases",
        json={"case_ids": case_ids},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["added"] == len(case_ids)


def _execute_manual(client, auth_headers, plan_id, status="pass"):
    detail = client.get(f"/api/v1/test-plans/{plan_id}", headers=auth_headers).json()["data"]
    pcase = detail["cases"][0]
    resp = client.post(
        f"/api/v1/test-plans/{plan_id}/cases/{pcase['id']}/execute",
        json={"status": status, "notes": "B149TMP-手动执行"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


class TestCaliberConsistency:
    """C147-3：dashboard / trace / plan-list 三端数字一致。"""

    def test_dashboard_and_trace_case_counts_ignore_deleted(self, db_session, client, auth_headers):
        from app.models.test_case import TestCase

        c1 = _create_case(client, auth_headers, title="B149TMP-功能用例")
        c2 = _create_case(client, auth_headers, title="B149TMP-接口用例", case_type="api")
        c3 = _create_case(client, auth_headers, title="B149TMP-已删除用例")
        row = db_session.get(TestCase, c3)
        row.is_deleted = True
        db_session.commit()

        dash = client.get("/api/v1/dashboard/stats", headers=auth_headers).json()["data"]
        assert dash["total_cases"] == 2
        assert dash["api_cases"] == 1

        trace = client.get("/api/v1/trace/coverage", headers=auth_headers).json()["data"]
        assert trace["total_cases"] == 2
        assert trace["by_type"]["manual"] == 1
        assert trace["by_type"]["api"] == 1
        assert "functional" not in trace["by_type"] or trace["by_type"].get("functional", 0) == 0

    def test_dashboard_execution_counts_match_test_execution(self, db_session, client, auth_headers):
        """执行计数不因用例删除丢失（修复 dashboard execution=0）。"""
        from app.models.test_case import TestCase

        c1 = _create_case(client, auth_headers, title="B149TMP-正常用例")
        c2 = _create_case(client, auth_headers, title="B149TMP-删除后仍有执行")
        plan = _create_plan(client, auth_headers)
        _add_cases(client, auth_headers, plan, [c1, c2])

        # 执行 c1（pass）；c2 先标记删除再执行（fail）→ 执行记录仍应计数
        _execute_manual(client, auth_headers, plan, status="pass")
        row = db_session.get(TestCase, c2)
        row.is_deleted = True
        db_session.commit()
        _execute_manual(client, auth_headers, plan, status="fail")

        dash = client.get("/api/v1/dashboard/stats", headers=auth_headers).json()["data"]
        assert dash["total_cases"] == 1  # c2 已删除
        assert sum(x["execution_total"] for x in dash["case_type_stats"]) == 2
        manual = next(x for x in dash["case_type_stats"] if x["case_type"] == "manual")
        assert manual["execution_total"] == 2
        assert manual["execution_pass"] == 1
        assert manual["execution_fail"] == 1
        assert dash["pass_rate"] == 50.0

    def test_trace_execution_counts(self, client, auth_headers):
        c1 = _create_case(client, auth_headers, title="B149TMP-追溯用例")
        plan = _create_plan(client, auth_headers)
        _add_cases(client, auth_headers, plan, [c1])
        _execute_manual(client, auth_headers, plan, status="pass")

        trace = client.get("/api/v1/trace/coverage", headers=auth_headers).json()["data"]
        assert trace["cases_in_plans"] == 1
        assert trace["cases_executed"] == 1
        assert trace["cases_passed"] == 1
        assert trace["pass_rate"] == 100.0


class TestPlanListStats:
    """C147-4：计划列表进度不再 0/0。"""

    def test_plan_list_returns_stats(self, client, auth_headers):
        c1 = _create_case(client, auth_headers, title="B149TMP-计划进度A")
        c2 = _create_case(client, auth_headers, title="B149TMP-计划进度B")
        plan = _create_plan(client, auth_headers, name="B149TMP-进度计划")
        _add_cases(client, auth_headers, plan, [c1, c2])
        _execute_manual(client, auth_headers, plan, status="pass")

        resp = client.get("/api/v1/test-plans", headers=auth_headers)
        assert resp.status_code == 200
        item = next(p for p in resp.json()["data"]["items"] if p["id"] == plan)
        assert item["stats"]["total"] == 2
        assert item["stats"]["pass_"] == 1
        assert item["stats"]["pending"] == 1
