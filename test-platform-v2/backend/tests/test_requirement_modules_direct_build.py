"""Batch 118 — C102-3 需求文档直建模块树（无需蓝湖证据包）。"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.models.requirement import RequirementDocument
from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle


def _document(
    db_session,
    *,
    title: str = "C102-3 直建文档",
    content: str = "# doc",
    extraction_raw: str = "",
    version: str = "1.2.0",
) -> RequirementDocument:
    doc = RequirementDocument(
        project_id=1,
        creator_id=1,
        title=title,
        file_type="md",
        source_ref=f"{title}.md",
        content=content,
        status="parsed",
        extraction_raw=extraction_raw,
        version=version,
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def _extraction_raw() -> str:
    return json.dumps({
        "modules": [
            {"name": "首页", "description": "首页模块", "function_points": [
                {"title": "热门比赛", "description": "展示热门比赛", "type": "functional"},
                {"title": "赛程表", "description": "赛程表模块", "type": "functional"},
            ]},
            {"name": "赛事详情", "description": "赛事详情模块", "function_points": [
                {"title": "视频直播", "description": "直播", "type": "functional"},
            ]},
        ],
    }, ensure_ascii=False)


def test_build_from_document_extraction_raw(client, auth_headers, db_session):
    doc = _document(db_session, extraction_raw=_extraction_raw())
    resp = client.post(
        "/api/v1/requirement-modules/build-from-document",
        json={"document_id": doc.id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["module_count"] == 2
    assert data["warnings"] == []

    bundle = db_session.scalar(
        select(ReleaseBundle).where(ReleaseBundle.project_id == 1)
    )
    assert bundle is not None
    assert bundle.name == doc.title

    modules = db_session.scalars(
        select(RequirementModule).where(
            RequirementModule.release_bundle_id == bundle.id,
            RequirementModule.node_type == "module",
        )
    ).all()
    assert len(modules) == 2
    assert {m.name for m in modules} == {"首页", "赛事详情"}

    fps = db_session.scalars(
        select(RequirementModule).where(
            RequirementModule.release_bundle_id == bundle.id,
            RequirementModule.node_type == "function_point",
        )
    ).all()
    assert len(fps) == 3


def test_build_from_document_existing_bundle(client, auth_headers, db_session):
    bundle = ReleaseBundle(
        project_id=1,
        name="已有发布包",
        client_version="1.1.0",
        status="draft",
    )
    db_session.add(bundle)
    db_session.flush()
    doc = _document(db_session, extraction_raw=_extraction_raw())
    resp = client.post(
        "/api/v1/requirement-modules/build-from-document",
        json={"document_id": doc.id, "release_bundle_id": bundle.id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    count = db_session.scalar(
        select(RequirementModule.id).where(
            RequirementModule.release_bundle_id == bundle.id,
            RequirementModule.node_type == "module",
        )
    )
    assert count is not None
    assert db_session.scalar(
        select(ReleaseBundle).where(ReleaseBundle.id == bundle.id)
    ).name == "已有发布包"


def test_build_from_document_content_fallback(client, auth_headers, db_session):
    content = (
        "# 体育平台\n"
        "## 首页\n"
        "### 热门比赛\n"
        "- 展示热门比赛列表\n"
        "- 点击进入赛事详情\n"
        "## 资讯\n"
        "### 资讯列表\n"
        "- 按分类筛选\n"
    )
    doc = _document(db_session, content=content, extraction_raw="")
    resp = client.post(
        "/api/v1/requirement-modules/build-from-document",
        json={"document_id": doc.id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["module_count"] == 2
    assert data["warnings"] == []


def test_build_from_document_missing(client, auth_headers, db_session):
    resp = client.post(
        "/api/v1/requirement-modules/build-from-document",
        json={"document_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 404


def test_build_from_document_other_project(client, auth_headers, db_session):
    doc = _document(db_session, extraction_raw=_extraction_raw())
    doc.project_id = 2
    db_session.flush()
    resp = client.post(
        "/api/v1/requirement-modules/build-from-document",
        json={"document_id": doc.id},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 404
