"""Batch 167 Phase 2 — 需求 integration 功能点绑定真实端点生成接口用例。"""
from __future__ import annotations

import json

from app.models.api_asset import ApiEndpoint, ApiService
from app.models.requirement import RequirementDocument
from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle
from app.models.test_case import TestCase
from app.services.requirement_service import generate_api_cases_from_linked_endpoints


def _make_doc_and_endpoint(db):
    svc = ApiService(project_id=1, name="camel-service", display_name="Camel Service")
    db.add(svc)
    db.flush()
    endpoint = ApiEndpoint(
        project_id=1, service_id=svc.id, module="赛事预测", method="POST",
        path="/forecast/queryOddsSummaryByMatchId", summary="按赛事查询赔率汇总",
        request_schema=json.dumps({
            "body": {
                "properties": {"matchId": {"type": "string", "description": "赛事 ID"}},
                "required": ["matchId"],
            },
            "query": [],
            "path": [],
            "header": [],
        }),
    )
    db.add(endpoint)
    db.flush()
    bundle = ReleaseBundle(project_id=1, name="B167-B", client_version="15.0.0")
    db.add(bundle)
    db.flush()
    mod = RequirementModule(project_id=1, release_bundle_id=bundle.id, name="赛事预测", node_type="module")
    db.add(mod)
    db.flush()
    doc = RequirementDocument(
        project_id=1, title="B167-预测", status="imported",
        extraction_raw=json.dumps({
            "modules": [{
                "name": "赛事预测",
                "function_points": [{
                    "id": "FP-1", "title": "查询赛事赔率汇总", "type": "integration",
                    "description": "按 matchId 查询赔率汇总",
                }],
            }],
        }),
    )
    db.add(doc)
    db.commit()
    return doc, endpoint, mod


def test_generates_cases_and_links_module(db_session):
    doc, endpoint, mod = _make_doc_and_endpoint(db_session)
    result = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert result["matched"] == 1
    assert result["generated"] >= 1
    assert result["upserted"] >= 1
    cases = db_session.query(TestCase).filter(
        TestCase.case_type == "api",
        TestCase.api_endpoint == endpoint.path,
    ).all()
    assert cases
    assert all(c.requirement_module_id == mod.id for c in cases)
    assert all(c.module == "赛事预测" for c in cases)
    # 幂等：重复调用不新增重复用例
    again = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert again["upserted"] == result["upserted"]
    count_after = db_session.query(TestCase).filter(
        TestCase.case_type == "api", TestCase.api_endpoint == endpoint.path,
    ).count()
    assert count_after == len(cases)


def test_no_endpoints_fails_closed(db_session):
    doc = RequirementDocument(
        project_id=1, title="B167-无端点", status="imported",
        extraction_raw=json.dumps({"modules": [{"name": "X", "function_points": [{"id": "FP-1", "title": "Y", "type": "integration"}]}]}),
    )
    db_session.add(doc)
    db_session.commit()
    result = generate_api_cases_from_linked_endpoints(db_session, doc_id=doc.id, project_id=1)
    assert result["matched"] == 0
    assert result["generated"] == 0


def test_endpoint_envelope(db_session, client, auth_headers):
    doc, _ep, _mod = _make_doc_and_endpoint(db_session)
    resp = client.post(f"/api/v1/requirements/{doc.id}/generate-api-from-endpoints", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["matched"] == 1
    assert data["generated"] >= 1

