"""Batch 118 — C102-4 生产页面 vs 需求原型差异标注。"""
from __future__ import annotations

from sqlalchemy import select

from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle


def _bundle(db_session, *, project_id: int = 1) -> ReleaseBundle:
    bundle = ReleaseBundle(
        project_id=project_id,
        name="C102-4 差异标注",
        client_version="1.0.0",
        status="draft",
    )
    db_session.add(bundle)
    db_session.flush()
    return bundle


def _module(db_session, bundle_id: int, name: str, node_type: str = "module") -> RequirementModule:
    node = RequirementModule(
        project_id=1,
        release_bundle_id=bundle_id,
        name=name,
        node_type=node_type,
        platform="WEB",
    )
    db_session.add(node)
    db_session.flush()
    return node


def _prod_pages():
    return [
        {"label": "首页", "title": "Home", "url": "https://www.target.example.com/"},
        {"label": "match-replay", "title": "Match Replays", "url": "/match-replay"},
        {"label": "资讯列表", "title": "News", "url": "/q/news"},
    ]


def test_compute_diff_classification(client, auth_headers, db_session):
    bundle = _bundle(db_session)
    _module(db_session, bundle.id, "首页")
    _module(db_session, bundle.id, "资讯")
    _module(db_session, bundle.id, "个人中心")

    resp = client.post(
        "/api/v1/requirement-modules/production-diff",
        json={"release_bundle_id": bundle.id, "production_pages": _prod_pages()},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    summary = data["summary"]
    assert summary["production_total"] == 3
    assert summary["requirement_total"] == 3
    assert summary["matched_count"] >= 1  # 首页 → 首页
    assert summary["new_count"] >= 1      # match-replay（World Cup/Replays 新模块）
    assert summary["missing_count"] >= 1  # 个人中心 未出现在生产清单

    change_types = {i["change_type"] for i in data["items"]}
    assert {"new", "matched", "missing"} <= change_types
    matched = next(i for i in data["items"] if i["change_type"] == "matched")
    assert matched["matched_with"] == "首页"


def test_diff_service_requirement_side(client, auth_headers, db_session):
    bundle = _bundle(db_session)
    _module(db_session, bundle.id, "首页")
    resp = client.post(
        "/api/v1/requirement-modules/production-diff",
        json={"release_bundle_id": bundle.id, "production_pages": [{"label": "不存在的页面"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["summary"]["new_count"] == 1
    assert data["summary"]["missing_count"] == 1


def test_diff_missing_bundle(client, auth_headers, db_session):
    resp = client.post(
        "/api/v1/requirement-modules/production-diff",
        json={"release_bundle_id": 999999, "production_pages": []},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 404


def test_diff_empty_bundle_warns(client, auth_headers, db_session):
    bundle = _bundle(db_session)
    resp = client.post(
        "/api/v1/requirement-modules/production-diff",
        json={"release_bundle_id": bundle.id, "production_pages": [{"label": "首页"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert any("暂无模块树" in w for w in resp.json()["data"]["warnings"])
