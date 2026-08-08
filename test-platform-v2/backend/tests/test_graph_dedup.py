"""Batch 124 — 图谱去重兜底测试：重复实体不导致 graph/view 崩溃且节点唯一。"""
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
    session.add(Project(id=1, code="DEDUP-TEST", name="Dedup Test"))
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
        u = User(id=1, username="dedup", password="x", nickname="D", email="d@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_graph_view_dedup_duplicate_entities(kclient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "knowledge_graph_enabled", True, raising=False)

    # 两个实体 entity_key 相同（历史重复）→ graph/view 必须去重不崩溃
    dup = {
        "entities": [
            {"entity_type": "test_case", "entity_key": "test_case:p1:首页热门赛事-真实分页参数", "name": "首页热门赛事-真实分页参数", "confidence": 1.0},
            {"entity_type": "test_case", "entity_key": "test_case:p1:首页热门赛事-真实分页参数", "name": "首页热门赛事-真实分页参数", "confidence": 1.0},
            {"entity_type": "module", "entity_key": "module:安卓iOS/赛事详情", "name": "安卓iOS/赛事详情", "confidence": 1.0},
        ],
        "relations": [
            {"from_key": "module:安卓iOS/赛事详情", "relation_type": "contains", "to_key": "test_case:p1:首页热门赛事-真实分页参数", "evidence": "e"},
        ],
    }
    r = kclient.post("/api/v1/knowledge/graph/module-associations", json=dup)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["created_entities"] == 2  # 第二个重复实体被跳过

    g = kclient.get("/api/v1/knowledge/graph/view")
    assert g.status_code == 200, g.text
    d = g.json()["data"]
    ids = [n["id"] for n in d["nodes"]]
    assert len(ids) == len(set(ids)), f"重复节点 id: {ids}"
    # 边指向有效节点
    valid = set(ids)
    for e in d["edges"]:
        assert e["source"] in valid and e["target"] in valid
