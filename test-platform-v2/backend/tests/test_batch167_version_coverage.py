"""Batch 167 Phase 0 — 版本级三类型模块覆盖矩阵回归。"""
from __future__ import annotations

from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.services.version_coverage_service import compute_bundle_coverage


def _add_case(db, module_name="首页", ctype="manual", priority="P0", requirement_module_id=None):
    case = TestCase(
        project_id=1, title=f"{ctype}-{module_name}", module=module_name,
        case_type=ctype, priority=priority,
        requirement_module_id=requirement_module_id,
    )
    db.add(case)
    db.flush()
    return case


def test_all_three_types_covered_and_gate(db_session):
    bundle = ReleaseBundle(project_id=1, name="B167", client_version="15.0.0")
    db_session.add(bundle)
    db_session.flush()
    m1 = RequirementModule(project_id=1, release_bundle_id=bundle.id, name="首页", node_type="module")
    m2 = RequirementModule(project_id=1, release_bundle_id=bundle.id, name="赛事详情", node_type="module")
    db_session.add_all([m1, m2])
    db_session.flush()
    _add_case(db_session, "首页", "manual", "P0", m1.id)
    _add_case(db_session, "首页", "api", "P0", m1.id)
    _add_case(db_session, "首页", "ui", "P0", m1.id)
    _add_case(db_session, "赛事详情", "manual", "P1", m2.id)
    db_session.commit()

    result = compute_bundle_coverage(db_session, bundle.id, 1)
    assert result["total_modules"] == 2
    assert result["covered_modules"] == 1
    assert result["covered_rate"] == 0.5
    assert result["gate_passed"] is False
    by_name = {row["name"]: row for row in result["rows"]}
    assert by_name["首页"]["covered"] is True
    assert by_name["首页"]["gap_types"] == []
    assert by_name["赛事详情"]["gap_types"] == ["api", "ui"]


def test_executed_coverage_requires_api_and_ui_execution(db_session):
    bundle = ReleaseBundle(project_id=1, name="B167", client_version="15.0.0")
    db_session.add(bundle)
    db_session.flush()
    mod = RequirementModule(project_id=1, release_bundle_id=bundle.id, name="首页", node_type="module")
    db_session.add(mod)
    db_session.flush()
    _add_case(db_session, "首页", "manual", "P0", mod.id)
    api = _add_case(db_session, "首页", "api", "P0", mod.id)
    ui = _add_case(db_session, "首页", "ui", "P0", mod.id)
    plan = TestPlan(project_id=1, name="B167-PLAN", status="active")
    db_session.add(plan)
    db_session.flush()
    for case in (api, ui):
        pc = TestPlanCase(plan_id=plan.id, case_id=case.id)
        db_session.add(pc)
        db_session.flush()
        db_session.add(TestExecution(plan_case_id=pc.id, status="pass"))
    db_session.commit()

    result = compute_bundle_coverage(db_session, bundle.id, 1)
    row = result["rows"][0]
    assert row["covered"] is True
    assert row["executed_covered"] is True
    assert result["executed_covered_modules"] == 1
    assert result["executed_covered_rate"] == 1.0


def test_empty_module_tree_falls_back_to_case_modules(db_session):
    bundle = ReleaseBundle(project_id=1, name="B167-EMPTY", client_version="15.0.0")
    db_session.add(bundle)
    db_session.flush()
    _add_case(db_session, "首页", "manual", "P0")
    db_session.commit()

    result = compute_bundle_coverage(db_session, bundle.id, 1)
    assert result["total_modules"] == 1
    assert result["rows"][0]["name"] == "首页"
    assert result["rows"][0]["gap_types"] == ["api", "ui"]


def test_coverage_endpoint_envelope(db_session, client, auth_headers):
    bundle = ReleaseBundle(project_id=1, name="B167-API", client_version="15.0.0")
    db_session.add(bundle)
    db_session.commit()
    resp = client.get(f"/api/v1/release-bundles/{bundle.id}/coverage", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["bundle_id"] == bundle.id
    assert data["target_rate_percent"] == 60.0
    assert "rows" in data
