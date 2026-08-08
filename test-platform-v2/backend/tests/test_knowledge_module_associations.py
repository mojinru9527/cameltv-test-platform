"""Batch 123 — 体育模块关联图谱入库端点测试（幂等 + 可查询）。"""
from __future__ import annotations

import pytest


@pytest.fixture()
def kdb():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    from app.models.project import Project
    session.add(Project(id=1, code="KNOWLEDGE-MA-TEST", name="MA Test"))
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
        u = User(id=1, username="matester", password="x", nickname="MA", email="ma@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _payload():
    return {
        "entities": [
            {"entity_type": "module", "entity_key": "module:安卓iOS/赛事详情", "name": "安卓iOS/赛事详情", "confidence": 1.0},
            {"entity_type": "module", "entity_key": "module:安卓iOS/赛事详情/预测Pick", "name": "安卓iOS/赛事详情/预测Pick", "confidence": 1.0},
            {"entity_type": "test_case", "entity_key": "test_case:SP-AND-PICK-001", "name": "预测中-下注成功", "confidence": 1.0},
            {"entity_type": "api", "entity_key": "api:POST:/ee/forecast/bet", "name": "/ee/forecast/bet", "confidence": 1.0},
        ],
        "relations": [
            {"from_key": "module:安卓iOS/赛事详情", "relation_type": "contains", "to_key": "module:安卓iOS/赛事详情/预测Pick", "evidence": "case:SP-AND-PICK-001"},
            {"from_key": "module:安卓iOS/赛事详情/预测Pick", "relation_type": "contains", "to_key": "test_case:SP-AND-PICK-001", "evidence": "case:SP-AND-PICK-001"},
            {"from_key": "api:POST:/ee/forecast/bet", "relation_type": "tested_by", "to_key": "test_case:SP-AND-PICK-001", "evidence": "case:SP-AND-PICK-001"},
        ],
    }


def test_module_associations_import_idempotent_and_visible(kclient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "knowledge_graph_enabled", True, raising=False)

    r1 = kclient.post("/api/v1/knowledge/graph/module-associations", json=_payload())
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    assert d1["created_entities"] == 4
    assert d1["created_relations"] == 3
    assert d1["skipped_entities"] == 0

    # 幂等：重复提交不重复创建
    r2 = kclient.post("/api/v1/knowledge/graph/module-associations", json=_payload())
    assert r2.status_code == 200, r2.text
    d2 = r2.json()["data"]
    assert d2["created_entities"] == 0
    assert d2["created_relations"] == 0
    assert d2["skipped_entities"] == 4
    assert d2["skipped_relations"] == 3

    # 图谱可查询到业务关系
    g = kclient.get("/api/v1/knowledge/graph/view")
    assert g.status_code == 200, g.text
    gd = g.json()["data"]
    rel_types = {e["relation_type"] for e in gd["edges"]}
    assert "tested_by" in rel_types
    assert "contains" in rel_types


def test_module_associations_requires_graph_enabled(kclient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "knowledge_graph_enabled", False, raising=False)
    r = kclient.post("/api/v1/knowledge/graph/module-associations", json=_payload())
    assert r.status_code == 503
