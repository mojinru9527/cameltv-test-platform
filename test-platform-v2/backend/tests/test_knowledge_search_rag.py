"""Phase P2 Task 6: RAG Enablement And Search Acceptance 测试。

覆盖：
- reembed 更新 embedding_id（RAG 开启时）
- 搜索项目隔离（跨 project_id 不可见）
- rag_enabled=False 时搜索优雅降级为关键词模式
- 搜索健康检查端点
- 概览端点包含 RAG 健康指标
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ═══════════════════════════════════════════════════════
# 自包含夹具（仿 test_knowledge.py，不依赖共享 conftest）
# ═══════════════════════════════════════════════════════

@pytest.fixture()
def kdb():
    """in-memory SQLite + StaticPool（跨线程共享）。"""
    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb):
    """TestClient + 超级用户直接注入（绕过登录），permissions=["*"] + project_id=1。"""
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="ragtester", password="x", nickname="RAG", email="rag@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════
# 确定性 bag-of-chars 向量替身（离线测试用）
# ═══════════════════════════════════════════════════════

def _bag_vec(text: str, dim: int = 32):
    import numpy as np

    v = np.zeros(dim, dtype=np.float32)
    for ch in text or "":
        v[ord(ch) % dim] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n else v


def _fake_embed(texts):
    import numpy as np

    return np.vstack([_bag_vec(t) for t in texts]).astype(np.float32)


def _patch_fake_embedder(monkeypatch):
    """替换 embedding_service 为确定性替身。"""
    from app.services.knowledge.embedding_service import embedding_service

    monkeypatch.setattr(embedding_service, "available", lambda: True)
    monkeypatch.setattr(embedding_service, "embed", _fake_embed)
    monkeypatch.setattr(embedding_service, "embed_query", lambda q: _bag_vec(q))
    monkeypatch.setattr(embedding_service, "_model_name", "bag-test")
    monkeypatch.setattr(embedding_service, "_dim", 32)
    return embedding_service


def _seed_chunks(db, texts, project_id=1, chunk_type="test_case"):
    """播种 KnowledgeSource + KnowledgeChunk。"""
    from app.models.knowledge import KnowledgeChunk, KnowledgeSource

    src = KnowledgeSource(project_id=project_id, source_type=chunk_type, title="源", status="parsed")
    db.add(src)
    db.flush()
    for t in texts:
        db.add(KnowledgeChunk(
            project_id=project_id, source_id=src.id, chunk_type=chunk_type,
            title=t[:20], content=t, status="active", embedding_id="",
        ))
    db.commit()
    return src


def _make_chunk(db, project_id=1, title="", content="", chunk_type="test_case", embedding_id=""):
    """创建单个 KnowledgeChunk（含 source）。"""
    from app.models.knowledge import KnowledgeChunk, KnowledgeSource

    src = KnowledgeSource(project_id=project_id, source_type=chunk_type, title=title or "源", status="parsed")
    db.add(src)
    db.flush()
    c = KnowledgeChunk(
        project_id=project_id, source_id=src.id, chunk_type=chunk_type,
        title=title, content=content, status="active", embedding_id=embedding_id,
    )
    db.add(c)
    db.commit()
    return c


# ═══════════════════════════════════════════════════════
# 测试：reembed
# ═══════════════════════════════════════════════════════

class TestReembed:
    def test_reembed_updates_embedding_id(self, kdb, kclient, monkeypatch):
        """RAG 开启 + fake embedder → reembed 应回填 embedding_id。"""
        from app.core.config import settings
        from app.services.knowledge import vectorize

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(vectorize, "SessionLocal", lambda: kdb)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["密码字段需要非空校验", "视频清晰度切换"], project_id=1)

        resp = kclient.post("/api/v1/knowledge/reembed")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["embedded"] >= 1

    def test_reembed_503_when_rag_disabled(self, kclient, monkeypatch):
        """RAG 关闭 → reembed 返回 503。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        resp = kclient.post("/api/v1/knowledge/reembed")
        assert resp.status_code == 503

    def test_reembed_503_when_model_unavailable(self, kclient, monkeypatch):
        """RAG 开启但模型不可用 → reembed 返回 503。"""
        from app.core.config import settings
        from app.services.knowledge.embedding_service import embedding_service

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(embedding_service, "available", lambda: False)
        resp = kclient.post("/api/v1/knowledge/reembed")
        assert resp.status_code == 503

    def test_reembed_idempotent(self, kdb, kclient, monkeypatch):
        """重复 reembed 不重复嵌入（embedding_id 已填充 → 跳过）。"""
        from app.core.config import settings
        from app.services.knowledge import vectorize

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(vectorize, "SessionLocal", lambda: kdb)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["内容A"], project_id=1)

        # 第一次：应嵌入
        r1 = kclient.post("/api/v1/knowledge/reembed")
        assert r1.status_code == 200
        assert r1.json()["data"]["embedded"] >= 1

        # 第二次：幂等，嵌入数为 0（跳过）
        r2 = kclient.post("/api/v1/knowledge/reembed")
        assert r2.status_code == 200
        assert r2.json()["data"]["embedded"] == 0


# ═══════════════════════════════════════════════════════
# 测试：搜索项目隔离
# ═══════════════════════════════════════════════════════

class TestSearchProjectIsolation:
    def test_search_returns_project_scoped_hits(self, kdb, kclient, monkeypatch):
        """搜索仅返回当前项目切片，跨项目数据不可见。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["比赛推送 matchId 必填"], project_id=1)
        _seed_chunks(kdb, ["越权内容 不应返回"], project_id=999)

        resp = kclient.post("/api/v1/knowledge/search", json={"query": "比赛推送", "top_k": 10})
        assert resp.status_code == 200
        items = resp.json()["data"]
        titles = [x["title"] for x in items]
        assert any("比赛推送" in t for t in titles)
        assert not any("越权内容" in t for t in titles)

    def test_keyword_search_filters_by_project(self, kdb, kclient, monkeypatch):
        """纯关键词搜索也仅返回当前项目切片。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["项目一专属内容"], project_id=1)
        _seed_chunks(kdb, ["项目二专属内容"], project_id=2)

        resp = kclient.post("/api/v1/knowledge/search", json={
            "query": "专属内容", "top_k": 10, "mode": "keyword",
        })
        assert resp.status_code == 200
        items = resp.json()["data"]
        titles = [x["title"] for x in items]
        assert any("项目一" in t for t in titles)
        assert not any("项目二" in t for t in titles)

    def test_vector_search_filters_by_project(self, kdb, kclient, monkeypatch):
        """向量搜索也仅返回当前项目切片。"""
        from app.models.knowledge import KnowledgeChunk
        from app.services.knowledge import vectorize
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["项目一专属内容"], project_id=1)
        _seed_chunks(kdb, ["项目二专属内容"], project_id=2)

        # 为所有切片嵌入向量
        all_chunks = kdb.query(KnowledgeChunk).all()
        vectorize._embed_and_store(kdb, all_chunks)
        kdb.commit()

        resp = kclient.post("/api/v1/knowledge/search", json={
            "query": "专属内容", "top_k": 10, "mode": "vector",
        })
        assert resp.status_code == 200
        items = resp.json()["data"]
        titles = [x["title"] for x in items]
        assert any("项目一" in t for t in titles)
        assert not any("项目二" in t for t in titles)


# ═══════════════════════════════════════════════════════
# 测试：rag_enabled=False 优雅降级
# ═══════════════════════════════════════════════════════

class TestRagDisabledGracefulDegradation:
    def test_search_falls_back_to_keyword(self, kdb, kclient, monkeypatch):
        """RAG 关闭时搜索自动降级为关键词模式，不报错。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        _seed_chunks(kdb, ["密码校验"], project_id=1)

        resp = kclient.post("/api/v1/knowledge/search", json={"query": "密码校验", "top_k": 5})
        assert resp.status_code == 200
        items = resp.json()["data"]
        # 关键词召回应能命中
        assert len(items) >= 1

    def test_search_falls_back_to_keyword_when_model_unavailable(self, kdb, kclient, monkeypatch):
        """模型不可用时搜索自动降级为关键词模式。"""
        from app.core.config import settings
        from app.services.knowledge.embedding_service import embedding_service

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(embedding_service, "available", lambda: False)
        _seed_chunks(kdb, ["密码校验"], project_id=1)

        resp = kclient.post("/api/v1/knowledge/search", json={"query": "密码校验", "top_k": 5})
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1

    def test_search_hybrid_request_downgraded_to_keyword(self, kdb, kclient, monkeypatch):
        """请求混合模式但 RAG 关闭 → 实际执行关键词搜索，仍返回结果。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        _seed_chunks(kdb, ["密码校验"], project_id=1)

        resp = kclient.post("/api/v1/knowledge/search", json={
            "query": "密码校验", "top_k": 5, "mode": "hybrid",
        })
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1


# ═══════════════════════════════════════════════════════
# 测试：搜索健康检查端点
# ═══════════════════════════════════════════════════════

class TestSearchHealth:
    def test_health_rag_disabled(self, kclient, monkeypatch):
        """RAG 关闭 → 健康检查报告 keyword-only 降级。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        resp = kclient.get("/api/v1/knowledge/search/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rag_enabled"] is False
        assert data["fallback_mode"] == "keyword-only"
        assert data["embedding_coverage"] is None

    def test_health_rag_enabled_no_vectors(self, kclient, monkeypatch):
        """RAG 开启但无向量记录 → vector_search_functional=False。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)
        resp = kclient.get("/api/v1/knowledge/search/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rag_enabled"] is True
        assert data["embedding_available"] is True
        assert data["vector_search_functional"] is False
        assert data["fallback_mode"] == "keyword-only"

    def test_health_rag_enabled_with_vectors(self, kdb, kclient, monkeypatch):
        """RAG 开启且有向量 → vector_search_functional=True。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)

        # 播种并嵌入一个切片
        c = _make_chunk(kdb, title="测试切片", content="有些内容", embedding_id="")  # empty first
        # 手动填充 embedding_id 模拟已完成向量回填
        from app.services.knowledge.vector_store import SqliteVectorStore
        store = SqliteVectorStore()
        store.upsert(kdb, chunk_id=c.id, project_id=1, model="bag-test", dim=32, vec=_bag_vec("有些内容"))
        c.embedding_id = str(c.id)  # 模拟 embedding_service 侧填充
        kdb.commit()

        resp = kclient.get("/api/v1/knowledge/search/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rag_enabled"] is True
        assert data["embedding_available"] is True
        assert data["vector_search_functional"] is True
        assert data["fallback_mode"] == "hybrid"

    def test_health_model_unavailable(self, kclient, monkeypatch):
        """模型不可用 → embedding_available=False。"""
        from app.core.config import settings
        from app.services.knowledge.embedding_service import embedding_service

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(embedding_service, "available", lambda: False)
        resp = kclient.get("/api/v1/knowledge/search/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["embedding_available"] is False
        assert data["fallback_mode"] == "keyword-only"


# ═══════════════════════════════════════════════════════
# 测试：概览端点 RAG 指标
# ═══════════════════════════════════════════════════════

class TestOverviewRagMetrics:
    def test_overview_includes_rag_fields(self, kclient, monkeypatch):
        """概览响应应包含 rag_enabled / embedding_model 等字段。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        resp = kclient.get("/api/v1/knowledge/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "rag_enabled" in data
        assert "embedding_model" in data
        assert "active_chunks" in data
        assert "embedded_chunks" in data
        assert "embedding_coverage" in data

    def test_overview_rag_disabled_coverage_null(self, kclient, monkeypatch):
        """RAG 关闭 → embedding_coverage=None。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        resp = kclient.get("/api/v1/knowledge/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rag_enabled"] is False
        assert data["embedding_coverage"] is None
        assert data["embedding_model"] == ""

    def test_overview_coverage_calculation(self, kdb, kclient, monkeypatch):
        """验证 embedding_coverage 正确计算。"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        # 3 个切片，1 个已嵌入
        _make_chunk(kdb, title="已嵌入", content="a", embedding_id="v1")
        _make_chunk(kdb, title="未嵌入1", content="b", embedding_id="")
        _make_chunk(kdb, title="未嵌入2", content="c", embedding_id="")

        resp = kclient.get("/api/v1/knowledge/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["active_chunks"] == 3
        assert data["embedded_chunks"] == 1
        assert data["embedding_coverage"] == pytest.approx(1 / 3, abs=0.01)
