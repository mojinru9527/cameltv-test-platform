"""DSH 测试 Agent 框架 — 开放 API 知识查询面单测（阶段 1）。

覆盖 /api/v1/open/knowledge/* 与 /open/requirements、/open/test-cases：
API Token 鉴权、project 隔离、检索/拓扑/用例回写。
"""
from __future__ import annotations

import hashlib

from app.models.api_token import ApiToken
from app.models.knowledge import KnowledgeEntity, KnowledgeRelation, KnowledgeSource
from app.models.requirement import RequirementDocument
from app.models.test_case import TestCase as TestCaseModel


def _mk_token(db, plain: str = "tpat_testknow", project_id: int = 1) -> ApiToken:
    token = ApiToken(
        project_id=project_id,
        name="agent-know",
        token_hash=hashlib.sha256(plain.encode()).hexdigest(),
        token_prefix=plain[:8],
        scopes='["read","write"]',
        enabled=True,
    )
    db.add(token)
    db.commit()
    return token


def _auth(plain: str = "tpat_testknow") -> dict:
    return {"Authorization": f"Bearer {plain}", "X-Project-Id": "1"}


# ── 知识源列表 ──

def test_open_sources_requires_token(client):
    resp = client.get("/api/v1/open/knowledge/sources")
    assert resp.status_code == 401


def test_open_sources_lists(db_session, client):
    _mk_token(db_session)
    db_session.add(KnowledgeSource(
        project_id=1, source_type="requirement", source_id="r1",
        title="登录需求", status="active", freshness_score=0.9,
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/knowledge/sources", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "登录需求"
    assert data["items"][0]["source_type"] == "requirement"


def test_open_sources_project_isolation(db_session, client):
    _mk_token(db_session)
    db_session.add(KnowledgeSource(
        project_id=2, source_type="requirement", source_id="r-other",
        title="别的项目", status="active",
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/knowledge/sources", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


def test_open_sources_filter_by_type(db_session, client):
    _mk_token(db_session)
    db_session.add_all([
        KnowledgeSource(project_id=1, source_type="requirement", source_id="r1", title="需求A", status="active"),
        KnowledgeSource(project_id=1, source_type="test_case", source_id="c1", title="用例B", status="active"),
    ])
    db_session.commit()

    resp = client.get("/api/v1/open/knowledge/sources?source_type=requirement", headers=_auth())
    assert resp.json()["data"]["total"] == 1
    assert resp.json()["data"]["items"][0]["title"] == "需求A"


# ── 检索 ──

def test_open_search_requires_query(db_session, client):
    _mk_token(db_session)
    resp = client.post("/api/v1/open/knowledge/search", json={}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["code"] == 400


def test_open_search_returns_hits(db_session, client, monkeypatch):
    from types import SimpleNamespace

    _mk_token(db_session)
    hits = [SimpleNamespace(
        chunk_id=1, chunk_type="requirement", title="登录需求",
        snippet="用户登录…", score=0.9, source_id=10, source_name="登录需求",
    )]
    captured = {}

    def fake_hybrid(db, *, project_id, query, top_k, chunk_type, mode):
        captured.update(project_id=project_id, query=query, top_k=top_k, mode=mode)
        return hits

    monkeypatch.setattr("app.services.knowledge.search_service.hybrid_search", fake_hybrid)

    resp = client.post("/api/v1/open/knowledge/search", json={"query": "登录", "top_k": 5}, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "登录需求"
    assert captured["project_id"] == 1
    assert captured["query"] == "登录"
    assert captured["top_k"] == 5


# ── 模块拓扑 ──

def test_open_module_topology_aggregates(db_session, client):
    _mk_token(db_session)
    mod = KnowledgeEntity(
        project_id=1, entity_type="module", entity_key="module:p1:登录",
        name="登录", description="登录模块", confidence=1.0, review_status="approved",
    )
    db_session.add(mod)
    db_session.flush()
    child = KnowledgeEntity(
        project_id=1, entity_type="test_case", entity_key="test_case:p1:TC-LOGIN-001",
        name="TC-LOGIN-001", description="登录成功", confidence=1.0, review_status="approved",
    )
    db_session.add(child)
    db_session.flush()
    db_session.add(KnowledgeRelation(
        project_id=1, from_entity_id=mod.id, to_entity_id=child.id,
        relation_type="contains", confidence=1.0, review_status="approved",
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/knowledge/modules", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    mod_out = data["modules"][0]
    assert mod_out["module"] == "登录"
    assert len(mod_out["related"]) == 1
    assert mod_out["related"][0]["entity_type"] == "test_case"
    assert mod_out["related"][0]["relation_type"] == "contains"


def test_open_module_topology_filter(db_session, client):
    _mk_token(db_session)
    db_session.add_all([
        KnowledgeEntity(project_id=1, entity_type="module", entity_key="module:p1:登录",
                        name="登录", confidence=1.0, review_status="approved"),
        KnowledgeEntity(project_id=1, entity_type="module", entity_key="module:p1:支付",
                        name="支付", confidence=1.0, review_status="approved"),
    ])
    db_session.commit()

    resp = client.get("/api/v1/open/knowledge/modules?module=登录", headers=_auth())
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["modules"][0]["module"] == "登录"


# ── 需求列表 ──

def test_open_requirements_lists(db_session, client):
    _mk_token(db_session)
    db_session.add(RequirementDocument(
        project_id=1, title="登录需求规格", version="1.0", source_ref="lanhu/login",
        status="uploaded", file_type="md",
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/requirements", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "登录需求规格"


# ── 用例列表/回写 ──

def test_open_test_cases_lists(db_session, client):
    _mk_token(db_session)
    db_session.add(TestCaseModel(
        project_id=1, case_id="TC-LOGIN-001", title="登录成功",
        module="登录", case_type="manual", priority="P1", status="active",
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/test-cases?module=登录", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["case_id"] == "TC-LOGIN-001"
    assert item["module"] == "登录"


def test_open_test_cases_project_isolation(db_session, client):
    _mk_token(db_session)
    db_session.add(TestCaseModel(
        project_id=2, case_id="TC-OTHER-001", title="别的项目",
        module="其他", case_type="manual", status="active",
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/test-cases", headers=_auth())
    assert resp.json()["data"]["total"] == 0


def test_open_test_cases_create(db_session, client):
    _mk_token(db_session)
    body = {
        "title": "Agent 生成：登录失败提示",
        "module": "登录",
        "case_type": "manual",
        "priority": "P1",
        "steps": '[{"action": "输入错误密码"}]',
        "expected_result": "提示密码错误",
        "source_req_id": "REQ-LOGIN-1",
        "source": "agent",
    }
    resp = client.post("/api/v1/open/test-cases", json=body, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Agent 生成：登录失败提示"
    assert data["id"]  # 入库返回主键

    # 已入库且 project 隔离生效
    row = db_session.get(TestCaseModel, data["id"])
    assert row is not None
    assert row.project_id == 1
    assert row.source == "agent"
    assert row.source_req_id == "REQ-LOGIN-1"


def test_open_test_cases_create_validation(db_session, client):
    _mk_token(db_session)
    # title 缺失/None → 字段校验失败转 400
    resp = client.post("/api/v1/open/test-cases", json={"title": None}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["code"] == 400


# ── 测试计划查询面（阶段 2 api-tester 编排入口）──

def test_open_plans_lists(db_session, client):
    from app.models.test_plan import TestPlan

    _mk_token(db_session)
    db_session.add(TestPlan(
        project_id=1, name="登录回归计划", plan_id="PLAN-LOGIN-1",
        status="active", creator_id=1,
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/plans", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["name"] == "登录回归计划"


def test_open_plans_project_isolation(db_session, client):
    from app.models.test_plan import TestPlan

    _mk_token(db_session)
    db_session.add(TestPlan(
        project_id=2, name="别的项目计划", plan_id="PLAN-OTHER-1",
        status="active", creator_id=1,
    ))
    db_session.commit()

    resp = client.get("/api/v1/open/plans", headers=_auth())
    assert resp.json()["data"]["total"] == 0


def test_open_plan_detail_404_other_project(db_session, client):
    from app.models.test_plan import TestPlan

    _mk_token(db_session)
    plan = TestPlan(project_id=2, name="别的项目计划", plan_id="PLAN-OTHER-1", status="active", creator_id=1)
    db_session.add(plan)
    db_session.commit()

    resp = client.get(f"/api/v1/open/plans/{plan.id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


def test_open_plan_executions_lists(db_session, client):
    from app.models.test_plan import TestPlan, TestPlanCase

    _mk_token(db_session)
    plan = TestPlan(project_id=1, name="登录回归计划", plan_id="PLAN-LOGIN-1", status="active", creator_id=1)
    db_session.add(plan)
    db_session.commit()
    db_session.add(TestPlanCase(plan_id=plan.id, case_id=1, sort_order=1))
    db_session.commit()

    resp = client.get(f"/api/v1/open/plans/{plan.id}/executions", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0  # 无执行记录返回空分页
