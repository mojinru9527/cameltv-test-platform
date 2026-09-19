"""Batch 260 / B3-3 — 「改了 X 要跑哪些」查询。

DoD（backlog B3-3）：查询 ≤2s；每条结论可点回原始用例/执行记录。
额外约束（Design §3 P3-2）：**查询条数不随模块数增长**（防 N+1）——本文件用 SQL 计数断言守着。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import event

from app.core.exceptions import APIException
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.models.test_plan import TestPlan, TestPlanCase
from app.services import impact_graph_service, impact_query_service


def _bundle(db, project_id: int = 1, version: str = "16.1.0") -> ReleaseBundle:
    bundle = ReleaseBundle(project_id=project_id, name=f"v{version}", client_version=version)
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return bundle


def _module(db, bundle, name: str, *, node_type="module", change_type=""):
    module = RequirementModule(
        project_id=bundle.project_id,
        release_bundle_id=bundle.id,
        name=name,
        node_type=node_type,
        change_type=change_type,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _case(db, project_id: int, module_name: str, *, case_type="api") -> TestCase:
    case = TestCase(project_id=project_id, title=f"{module_name}-{case_type}", module=module_name, case_type=case_type)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _plan_with_result(db, project_id: int, case: TestCase, *, status="pass", days_ago=1):
    plan = TestPlan(project_id=project_id, name=f"plan-{case.id}")
    db.add(plan)
    db.commit()
    db.refresh(plan)
    plan_case = TestPlanCase(
        plan_id=plan.id,
        case_id=case.id,
        last_status=status,
        last_executed_at=datetime.now() - timedelta(days=days_ago),
    )
    db.add(plan_case)
    db.commit()
    db.refresh(plan_case)
    return plan, plan_case


class TestWhatToRun:
    def test_returns_grouped_cases_with_traceable_refs(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育", change_type="new")
        api_case = _case(db_session, 1, "体育", case_type="api")
        ui_case = _case(db_session, 1, "体育", case_type="ui")
        manual_case = _case(db_session, 1, "体育", case_type="manual")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)

        result = impact_query_service.what_to_run(db_session, project_id=1, module="体育")

        assert result["counts"]["cases_total"] == 3
        assert {item["case_id"] for item in result["cases"]["api"]} == {api_case.id}
        assert {item["case_id"] for item in result["cases"]["ui"]} == {ui_case.id}
        assert {item["case_id"] for item in result["cases"]["functional"]} == {manual_case.id}
        # 结论可回溯：每条都带 ref
        assert all(item["ref"].startswith("case:") for group in result["cases"].values() for item in group)

    def test_includes_last_execution_per_case(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育")
        case = _case(db_session, 1, "体育")
        _plan_with_result(db_session, 1, case, status="fail", days_ago=2)
        newer_plan, _pc = _plan_with_result(db_session, 1, case, status="pass", days_ago=1)
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)

        result = impact_query_service.what_to_run(db_session, project_id=1, module="体育")

        assert result["last_runs"], "应带出最近一次执行结果"
        latest = result["last_runs"][0]
        assert latest["status"] == "pass"  # 取更近的一次，而不是更早的
        assert latest["plan_id"] == newer_plan.id
        assert latest["ref"] == f"plan:{newer_plan.id}"

    def test_reports_gaps_for_modules_without_cases(self, db_session):
        bundle = _bundle(db_session)
        covered = _module(db_session, bundle, "体育直播")
        _module(db_session, bundle, "体育积分")  # 无用例 → 缺口
        _case(db_session, 1, "体育直播")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)

        result = impact_query_service.what_to_run(db_session, project_id=1, module="体育")

        assert "体育积分" in result["gaps"]
        assert "体育直播" not in result["gaps"]
        assert result["counts"]["gaps"] == 1
        assert covered.name in result["affected_modules"]

    def test_affected_modules_include_upstream_dependents(self, db_session):
        bundle = _bundle(db_session)
        parent = _module(db_session, bundle, "赛事")
        child = _module(db_session, bundle, "直播")
        child.parent_module_id = parent.id
        db_session.commit()
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)

        result = impact_query_service.what_to_run(db_session, project_id=1, module="赛事")

        # 直播 depends 赛事 → 赛事被改动时直播也受影响
        assert "赛事" in result["affected_modules"]
        assert "直播" in result["affected_modules"]

    def test_empty_module_argument_is_rejected(self, db_session):
        with pytest.raises(APIException):
            impact_query_service.what_to_run(db_session, project_id=1, module="  ")

    def test_unknown_version_returns_readable_empty_result(self, db_session):
        result = impact_query_service.what_to_run(db_session, project_id=1, module="体育", version="9.9.9")
        assert result["counts"]["cases_total"] == 0
        assert "版本" in result.get("reason", "")

    def test_project_isolation(self, db_session):
        bundle1 = _bundle(db_session, project_id=1)
        _module(db_session, bundle1, "体育")
        bundle2 = _bundle(db_session, project_id=2)
        _module(db_session, bundle2, "体育")
        result = impact_query_service.what_to_run(db_session, project_id=2, module="体育")
        assert result["counts"]["affected_modules"] == 1


class TestNoNPlusOne:
    """查询条数必须与模块/用例数量无关（Design §3 P3-2）。"""

    def test_api_exposes_the_query(self, db_session, client, auth_headers):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育")
        _case(db_session, 1, "体育")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)

        resp = client.get(
            "/api/v1/impact/what-to-run", params={"module": "体育"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["counts"]["cases_total"] == 1
        assert set(data["cases"].keys()) == {"functional", "api", "ui"}
        assert data["refs"]["cases"] == [f"case:{data['cases']['api'][0]['case_id']}"]

    def test_api_requires_authentication(self, db_session, client):
        resp = client.get("/api/v1/impact/what-to-run", params={"module": "体育"})
        assert resp.status_code in (401, 403)

    def test_rebuild_endpoint_runs_the_builder(self, db_session, client, auth_headers):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育", change_type="new")
        resp = client.post(
            "/api/v1/impact/rebuild",
            json={"bundle_id": bundle.id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["created"] == 1
        assert resp.json()["data"]["coverage"]["total_modules"] == 1

    def test_static_path_is_not_shadowed(self, client, auth_headers):
        """bug-guard：静态路径不得被同前缀的路径参数抢匹配（本 router 目前无路径参数，作为回归保险）。"""
        resp = client.get(
            "/api/v1/impact/what-to-run", params={"module": "x"}, headers=auth_headers
        )
        assert resp.status_code != 422

    def _count_queries(self, db_session, project_id: int, module: str) -> int:
        statements: list[str] = []

        def _record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", _record)
        try:
            impact_query_service.what_to_run(db_session, project_id=project_id, module=module)
        finally:
            event.remove(engine, "before_cursor_execute", _record)
        return len(statements)

    def test_query_count_is_flat_as_cases_grow(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育")
        for index in range(3):
            _case(db_session, 1, "体育", case_type="api" if index % 2 == 0 else "ui")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        small = self._count_queries(db_session, 1, "体育")

        for index in range(30):
            _case(db_session, 1, "体育", case_type="api")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        large = self._count_queries(db_session, 1, "体育")

        assert large == small, f"查询条数随用例数增长：{small} → {large}（疑似 N+1）"

    def test_query_count_is_flat_as_modules_grow(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        small = self._count_queries(db_session, 1, "体育")

        for index in range(25):
            _module(db_session, bundle, f"体育子模块{index}")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        large = self._count_queries(db_session, 1, "体育")

        assert large == small, f"查询条数随模块数增长：{small} → {large}（疑似 N+1）"
