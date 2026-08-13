"""Batch 168 — 覆盖矩阵/接口生成/UI 变体/执行环境 修复回归。"""
from __future__ import annotations

import json

from app.models.api_asset import ApiEndpoint, ApiService
from app.models.environment import Environment
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.models.test_plan import TestPlan, TestPlanCase
from app.services import test_plan_service
from app.services.requirement_service import (
    generate_api_cases_from_linked_endpoints,
    import_cases,
)
from app.services.version_coverage_service import compute_bundle_coverage


def _case(db, module, ctype, priority="P0", source_doc_id=None, source_case_index=None):
    c = TestCase(
        project_id=1, title=f"{ctype}-{module}-{priority}", module=module,
        case_type=ctype, priority=priority, source_doc_id=source_doc_id,
        source_case_index=source_case_index,
    )
    db.add(c)
    db.flush()
    return c


def test_coverage_fallback_counts_per_module(db_session):
    bundle = ReleaseBundle(project_id=1, name="B168-F", client_version="16.0.0")
    db_session.add(bundle)
    db_session.flush()
    _case(db_session, "首页", "manual", "P0")
    _case(db_session, "首页", "api", "P0")
    _case(db_session, "首页", "ui", "P0")
    _case(db_session, "赛事详情", "manual", "P2")
    db_session.commit()

    result = compute_bundle_coverage(db_session, bundle.id, 1)
    assert result["total_modules"] == 2
    by_name = {r["name"]: r for r in result["rows"]}
    assert by_name["首页"]["functional_count"] == 1
    assert by_name["首页"]["api_count"] == 1
    assert by_name["首页"]["ui_count"] == 1
    assert by_name["首页"]["covered"] is True
    assert by_name["首页"]["is_p0p1"] is True
    assert by_name["赛事详情"]["functional_count"] == 1
    assert by_name["赛事详情"]["is_p0p1"] is False
    assert by_name["赛事详情"]["gap_types"] == ["api", "ui"]
    assert result["covered_modules"] == 1
    assert result["p0p1_modules"] == 1


def test_coverage_fallback_prefers_bundle_linked_docs(db_session):
    bundle = ReleaseBundle(project_id=1, name="B168-L", client_version="16.0.0")
    db_session.add(bundle)
    db_session.flush()
    doc = RequirementDocument(project_id=1, title="16.0.0 需求", status="imported",
                              release_bundle_id=bundle.id)
    db_session.add(doc)
    db_session.flush()
    _case(db_session, "广告展示规则", "manual", "P0", source_doc_id=doc.id, source_case_index=0)
    _case(db_session, "15.0.0-其他模块", "manual", "P1", source_doc_id=999, source_case_index=1)
    db_session.commit()

    result = compute_bundle_coverage(db_session, bundle.id, 1)
    assert result["total_modules"] == 1
    assert result["rows"][0]["name"] == "广告展示规则"


def _make_doc_endpoint(db, module_name="赛事预测", fp_title="查询赛事赔率汇总",
                       fp_type="integration", path="/forecast/queryOddsSummaryByMatchId",
                       method="POST", ep_module="赛事预测", summary="按赛事查询赔率汇总"):
    svc = ApiService(project_id=1, name="camel-service", display_name="Camel Service")
    db.add(svc)
    db.flush()
    endpoint = ApiEndpoint(
        project_id=1, service_id=svc.id, module=ep_module, method=method, path=path,
        summary=summary, request_schema=json.dumps({"body": {"properties": {}, "required": []}}),
    )
    db.add(endpoint)
    db.flush()
    doc = RequirementDocument(
        project_id=1, title="B168-DOC", status="imported",
        extraction_raw=json.dumps({
            "modules": [{
                "name": module_name,
                "function_points": [{
                    "id": "FP-1", "title": fp_title, "type": fp_type,
                    "description": "查询赔率汇总",
                }],
            }],
        }),
    )
    db.add(doc)
    db.commit()
    return doc, endpoint


def test_generate_skips_soft_deleted_rows_and_keeps_variants(db_session):
    doc, endpoint = _make_doc_endpoint(db_session)
    r1 = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert r1["generated"] >= 3
    active = db_session.query(TestCase).filter(
        TestCase.project_id == 1, TestCase.case_type == "api",
        TestCase.api_endpoint == endpoint.path, TestCase.is_deleted.is_(False),
    ).all()
    assert len(active) == r1["generated"]
    distinct_titles = {c.title for c in active}
    assert len(distinct_titles) == len(active)
    # 软删除一条后重跑：不复活删除行，而是新建可见行，幂等不回退
    victim = active[0]
    victim.is_deleted = True
    db_session.commit()
    r2 = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert r2["generated"] == r1["generated"]
    after = db_session.query(TestCase).filter(
        TestCase.project_id == 1, TestCase.case_type == "api",
        TestCase.api_endpoint == endpoint.path, TestCase.is_deleted.is_(False),
    ).all()
    assert len(after) == r1["generated"]
    assert any(c.title == victim.title and c.id != victim.id for c in after)


def test_module_level_match_binds_real_endpoint(db_session):
    # 模块内没有 integration FP，只有 functional FP → 走模块级兜底匹配
    doc, endpoint = _make_doc_endpoint(
        db_session, module_name="篮球相关-赛事详情页调整", fp_title="赛事详情页功能点",
        fp_type="functional", path="/ee/sports_live/football/match/analysis",
        method="GET", ep_module="sports-live-controller", summary="football match analysis",
    )
    extraction = json.loads(doc.extraction_raw)
    extraction["modules"][0]["description"] = "篮球 赛事详情页调整"
    doc.extraction_raw = json.dumps(extraction)
    db_session.commit()
    result = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert result["matched"] >= 1
    assert result["endpoints"][0]["source"] == "module"
    assert result["endpoints"][0]["module"] == "篮球相关-赛事详情页调整"
    cases = db_session.query(TestCase).filter(
        TestCase.project_id == 1, TestCase.case_type == "api",
        TestCase.api_endpoint == endpoint.path, TestCase.is_deleted.is_(False),
    ).all()
    assert cases
    assert all(c.module == "篮球相关-赛事详情页调整" for c in cases)


def test_import_creates_ui_variants_for_existing_cases(db_session):
    doc = RequirementDocument(
        project_id=1, title="B168-老数据", status="imported",
        imported_func_indices=json.dumps([0]),
    )
    db_session.add(doc)
    db_session.flush()
    pc = _case(
        db_session, "首页", "manual", "P0",
        source_doc_id=doc.id, source_case_index=0,
    )
    pc.steps = json.dumps([{"step": 1, "desc": "打开首页", "expected": "看到首页"}])
    db_session.commit()

    result = import_cases(db_session, doc.id, [], project_id=1, create_ui_cases=True, commit=True)
    assert result["ui_created"] == 1
    ui_cases = db_session.query(TestCase).filter(
        TestCase.project_id == 1, TestCase.case_type == "ui",
        TestCase.title == "[UI] manual-首页-P0",
    ).all()
    assert len(ui_cases) == 1
    # 幂等：再次调用不重复生成
    again = import_cases(db_session, doc.id, [], project_id=1, create_ui_cases=True, commit=True)
    assert again.get("ui_created", 0) == 0


def test_execute_all_uses_separate_ui_environment(db_session, monkeypatch):
    plan = TestPlan(project_id=1, name="B168-PLAN", status="draft")
    db_session.add(plan)
    db_session.flush()
    case = TestCase(
        project_id=1, title="首页直播列表", module="首页", case_type="manual",
        priority="P0", steps=json.dumps([{"step": 1, "desc": "打开首页", "expected": "看到直播列表"}]),
    )
    db_session.add(case)
    db_session.flush()
    pc = TestPlanCase(plan_id=plan.id, case_id=case.id)
    db_session.add(pc)
    db_session.flush()
    api_env = Environment(project_id=1, name="api", env_type="prod", base_url="https://api.cameltv.live")
    ui_env = Environment(project_id=1, name="ui", env_type="prod", base_url="https://www.camel1.tv")
    db_session.add_all([api_env, ui_env])
    db_session.commit()
    seen = {}

    def fake_exec(tc, base_url="", storage_state=None):
        seen["base_url"] = base_url
        return {"ok": False, "exit_code": 1, "stdout_tail": "assertion failed: expected 首页"}

    monkeypatch.setattr(test_plan_service, "_execute_ui_case_sync", fake_exec)
    monkeypatch.setattr(test_plan_service, "_write_plan_ui_job", lambda *a, **k: None)
    result = test_plan_service.execute_all_cases(
        db_session, plan.id, project_id=1, environment_id=api_env.id, ui_environment_id=ui_env.id,
    )
    assert seen["base_url"] == "https://www.camel1.tv"
    assert result["failed"] == 1
    assert "assertion failed" in result["details"][0].get("error", "")


def test_ui_error_summary_readable():
    summary = test_plan_service._ui_error_summary({"ok": False, "exit_code": 1, "stdout_tail": "timeout waiting for selector"})
    assert "exit_code=1" in summary
    assert "timeout waiting" in summary
    assert test_plan_service._ui_error_summary({"ok": False}) == "未知"

def test_real_tree_scopes_to_bundle_cases_only(db_session):
    """有真实模块树时，其它版本同名/相似模块用例不得污染本版本计数。"""
    bundle = ReleaseBundle(project_id=1, name="B168-S", client_version="16.0.0")
    db_session.add(bundle)
    db_session.flush()
    mod = RequirementModule(project_id=1, release_bundle_id=bundle.id, name="首页", node_type="module")
    db_session.add(mod)
    db_session.flush()
    in_tree = TestCase(project_id=1, title="in", module="首页", case_type="manual", priority="P0", requirement_module_id=mod.id)
    out_tree = TestCase(project_id=1, title="out", module="首页", case_type="manual", priority="P0")
    db_session.add_all([in_tree, out_tree])
    db_session.commit()
    result = compute_bundle_coverage(db_session, bundle.id, 1)
    row = result["rows"][0]
    assert row["functional_count"] == 1
