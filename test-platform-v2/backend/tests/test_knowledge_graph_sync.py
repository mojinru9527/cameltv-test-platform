"""Batch 132 — 全量用例入图 + 计数口径 + 分域隔离测试。

自包含 StaticPool 夹具（同 test_knowledge.py 模式），直接注入超级用户绕过登录。
"""
from __future__ import annotations

import pytest

from app.core.config import settings


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
    session.add(Project(id=1, code="B132", name="Batch 132 Project"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb, monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    monkeypatch.setattr(settings, "knowledge_graph_enabled", True)

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="ktester", password="x", nickname="K", email="k@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _seed_cases(db, count: int = 3) -> None:
    from app.models.test_case import TestCase
    for i in range(count):
        db.add(TestCase(
            project_id=1,
            case_id=f"B132-CASE-{i}",
            title=f"用例 {i}",
            domain="用户端/赛事详情",
            module="预测Pick" if i % 2 == 0 else "预测Pick/入口",
            case_type="manual",
            positive_negative="positive",
            is_deleted=False,
        ))
    db.commit()


class TestGraphSync:
    def test_sync_creates_entities_for_all_cases_and_backfills_source(self, kdb, kclient):
        _seed_cases(kdb, 3)
        resp = kclient.post("/api/v1/knowledge/graph/sync-test-cases")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cases"] == 3
        assert data["test_case_entities"] == 3

        from app.models.knowledge import KnowledgeEntity, KnowledgeSource
        library = kdb.query(KnowledgeSource).filter_by(
            project_id=1, source_type="test_case", title="用例库全量",
        ).first()
        assert library is not None
        assert library.knowledge_domain == "project"
        entities = kdb.query(KnowledgeEntity).filter_by(project_id=1, entity_type="test_case").all()
        assert len(entities) == 3
        assert all(e.source_id == library.id for e in entities)
        assert all(e.business_ref_id is not None for e in entities)

    def test_sync_is_idempotent(self, kdb, kclient):
        _seed_cases(kdb, 2)
        r1 = kclient.post("/api/v1/knowledge/graph/sync-test-cases").json()["data"]
        r2 = kclient.post("/api/v1/knowledge/graph/sync-test-cases").json()["data"]
        assert r1["test_case_entities"] == 2
        assert r2["test_case_entities"] == 2
        assert r2["created"] == 0


class TestStatsAndDomain:
    def test_stats_reports_library_total_and_domain_filter(self, kdb, kclient):
        _seed_cases(kdb, 5)
        from app.models.knowledge import KnowledgeEntity, KnowledgeSource
        proj_src = KnowledgeSource(project_id=1, source_type="manual", title="项目源", knowledge_domain="project", status="active")
        plat_src = KnowledgeSource(project_id=1, source_type="manual", title="平台源", knowledge_domain="platform", status="active")
        kdb.add_all([proj_src, plat_src])
        kdb.flush()
        kdb.add_all([
            KnowledgeEntity(project_id=1, entity_type="module", entity_key="m:proj", name="项目模块", source_id=proj_src.id, review_status="approved"),
            KnowledgeEntity(project_id=1, entity_type="module", entity_key="m:plat", name="平台模块", source_id=plat_src.id, review_status="approved"),
            KnowledgeEntity(project_id=1, entity_type="api", entity_key="api:orphan", name="孤儿API", source_id=None, review_status="approved"),
        ])
        kdb.commit()

        stats = kclient.get("/api/v1/knowledge/graph/entities/stats").json()["data"]
        assert stats["test_case_total"] == 5
        assert stats["by_type"].get("module", 0) == 2
        assert stats["by_type"].get("api", 0) == 1

        plat = kclient.get("/api/v1/knowledge/graph/entities/stats", params={"knowledge_domain": "platform"}).json()["data"]
        assert plat["by_type"].get("module", 0) == 1
        assert "api" not in plat["by_type"]  # 孤儿不归属平台域

        proj = kclient.get("/api/v1/knowledge/graph/entities/stats", params={"knowledge_domain": "project"}).json()["data"]
        assert proj["by_type"].get("module", 0) == 1  # 仅项目源模块
        assert proj["by_type"].get("api", 0) == 1     # 孤儿默认归项目域

    def test_graph_view_domains_are_disjoint(self, kdb, kclient):
        from app.models.knowledge import KnowledgeEntity, KnowledgeSource
        plat_src = KnowledgeSource(project_id=1, source_type="manual", title="平台源", knowledge_domain="platform", status="active")
        kdb.add(plat_src)
        kdb.flush()
        kdb.add_all([
            KnowledgeEntity(project_id=1, entity_type="module", entity_key="m:plat", name="平台模块", source_id=plat_src.id, review_status="approved"),
            KnowledgeEntity(project_id=1, entity_type="api", entity_key="api:orphan", name="孤儿API", source_id=None, review_status="approved"),
        ])
        kdb.commit()

        plat_nodes = kclient.get("/api/v1/knowledge/graph/view", params={"knowledge_domain": "platform", "limit": 1000}).json()["data"]["nodes"]
        proj_nodes = kclient.get("/api/v1/knowledge/graph/view", params={"knowledge_domain": "project", "limit": 1000}).json()["data"]["nodes"]
        plat_ids = {n["entity_id"] for n in plat_nodes}
        proj_ids = {n["entity_id"] for n in proj_nodes}
        assert any(n["name"] == "平台模块" for n in plat_nodes)
        assert any(n["name"] == "孤儿API" for n in proj_nodes)
        assert plat_ids.isdisjoint(proj_ids)
