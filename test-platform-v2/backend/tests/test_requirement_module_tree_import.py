"""Batch 124 — 需求模块树导入端点测试（层级 parent + 幂等）。"""
from __future__ import annotations

import pytest


@pytest.fixture()
def kdb():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    from app.models.project import Project
    session.add(Project(id=1, code="MODTREE-TEST", name="ModTree Test"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="modtree", password="x", nickname="MT", email="mt@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _payload():
    return {"bundle_name": "测试需求模块树", "source_version": "e6b5ce1e", "tree": [
        {"path": "运营后台/赛事预测", "type": "module", "lanhu_page_id": ""},
        {"path": "运营后台/赛事预测/预测赛事列表", "type": "page", "lanhu_page_id": "预测赛事列表.html", "screenshots": ["u1.png"]},
        {"path": "用户端/预测Pick", "type": "module", "lanhu_page_id": ""},
        {"path": "用户端/预测Pick/预测", "type": "page", "lanhu_page_id": "预测.html", "screenshots": ["u12.png"]},
    ]}


def test_import_module_tree_hierarchy_idempotent(kclient):
    r1 = kclient.post("/api/v1/requirement-modules/import-tree", json=_payload())
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    assert d1["created"] == 4
    assert d1["total"] == 4

    # 幂等
    r2 = kclient.post("/api/v1/requirement-modules/import-tree", json=_payload())
    assert r2.status_code == 200
    assert r2.json()["data"]["created"] == 0
    assert r2.json()["data"]["skipped"] == 4

    # 层级：页面挂在模块下（走 API 验证）
    lst = kclient.get("/api/v1/requirement-modules", params={"page_size": 50}).json()["data"]["items"]
    page = next((m for m in lst if m.get("name") == "预测赛事列表" and m.get("node_type") == "page"), None)
    assert page is not None, "页面未入库"
    assert page.get("node_type") == "page"
    detail = kclient.get(f"/api/v1/requirement-modules/{page['id']}").json()["data"]
    assert detail.get("parent_module_id") is not None
    parent = kclient.get(f"/api/v1/requirement-modules/{detail['parent_module_id']}").json()["data"]
    assert parent["name"] == "赛事预测"
    assert parent["node_type"] == "module"
    assert "u1.png" in (detail.get("screenshot_urls") or "")
