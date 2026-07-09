"""知识中心 M0+M1 测试 —— 模型/入库去重/脱敏/治理守卫/API 访问控制。"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException


# ═══════════════════════════════════════════════════════
# 自包含 API 夹具
#   共享 conftest 的 client/auth_headers 在当前工作树下受两处环境漂移影响：
#   (1) :memory: 跨线程无 StaticPool → "no such table"；(2) 登录响应体 shape 漂移
#   → KeyError('token')。二者均与本特性无关，故本文件自带 StaticPool 引擎 +
#   依赖覆盖（直接注入超级用户，绕过登录），保证 API 测试稳定可跑。
# ═══════════════════════════════════════════════════════

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
        u = User(id=1, username="ktester", password="x", nickname="K", email="k@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════
# 模型持久化 + default
# ═══════════════════════════════════════════════════════

class TestKnowledgeModels:
    def test_source_persist_defaults(self, db_session):
        from app.models.knowledge import KnowledgeSource
        s = KnowledgeSource(project_id=1, source_type="requirement", title="需求A", raw_content="hello")
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)
        assert s.status == "pending"
        assert s.metadata_json == "{}"
        assert s.created_at is not None

    def test_chunk_and_artifact_and_run_persist(self, db_session):
        from app.models.knowledge import AgentRun, AiArtifact, KnowledgeChunk
        c = KnowledgeChunk(project_id=1, source_id=1, chunk_type="test_case", content="x")
        a = AiArtifact(project_id=1, artifact_type="test_case", title="用例草稿")
        r = AgentRun(project_id=1, agent_type="case_generation")
        db_session.add_all([c, a, r])
        db_session.commit()
        assert c.status == "active"
        assert a.review_status == "pending"
        assert r.status == "pending"


# ═══════════════════════════════════════════════════════
# 脱敏
# ═══════════════════════════════════════════════════════

class TestSanitize:
    def test_masks_sensitive(self):
        from app.services.knowledge.sanitize import sanitize
        raw = (
            "Authorization: Bearer abc123.tok\n"
            '"password": "p@ss"\n'
            "联系 13812345678 邮箱 z@camel.to 证件 110101199001011234"
        )
        out = sanitize(raw)
        assert "abc123.tok" not in out
        assert "p@ss" not in out
        assert "13812345678" not in out and "138****5678" in out
        assert "z@camel.to" not in out
        assert "110101199001011234" not in out

    def test_masks_bypass_variants(self):
        """QA #1 回归：查询串/裸 JWT/行内 Cookie/带分隔符手机号/单引号 JSON 均须遮蔽。"""
        from app.services.knowledge.sanitize import sanitize

        # 查询串 & 表单 token（无引号）
        assert "supersecret" not in sanitize("GET /login?access_token=supersecret&x=1")
        assert "formtok123" not in sanitize("token=formtok123")
        # 裸 JWT（无 Bearer 前缀）
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.s3cr3tSig"
        assert "s3cr3tSig" not in sanitize(f"resp body: {jwt}")
        # 行内（非行首）Cookie
        assert "sessionval" not in sanitize("请求头里带了 Cookie: SID=sessionval; path=/")
        # 带分隔符手机号
        assert "138-1234-5678" not in sanitize("电话 138-1234-5678")
        assert "138 1234 5678" not in sanitize("电话 138 1234 5678")
        # 单引号 JSON
        assert "singleq" not in sanitize("body={'token': 'singleq'}")

    def test_masks_unquoted_and_colon_secrets(self):
        """Leader 复审残留缺口：冒号-无引号密钥、JSON 无引号值、点分隔手机号。"""
        from app.services.knowledge.sanitize import sanitize
        assert "hunter2" not in sanitize("password: hunter2")
        assert "colontok" not in sanitize("token: colontok")
        assert "998877" not in sanitize('{"api_key":998877}')
        assert "138.1234.5678" not in sanitize("电话 138.1234.5678")

    def test_sanitize_keeps_ordinary_text(self):
        """脱敏不得误伤普通文本（authorization 作为普通词、无 : / = 时不遮蔽；中文值保留）。"""
        from app.services.knowledge.sanitize import sanitize
        txt = "用户授权 authorization flow 设计 design 正常保留"
        assert sanitize(txt) == txt
        # 中文密钥说明不应被无引号规则误伤（值非 ASCII 起头）
        assert "表示令牌" in sanitize("token: 表示令牌")

    def test_sanitize_no_redos_on_large_blob(self):
        """Leader R2 复审 NEW P2 回归：大 blob 上脱敏须线性完成，杜绝 O(n²) ReDoS。"""
        import time
        from app.services.knowledge.sanitize import sanitize

        # 50KB 无 @ 的字母数字串——旧 _EMAIL_RE 会在此触发二次方回溯
        blob = ("a1b2c3d4e5" * 5000) + " tail"
        start = time.perf_counter()
        out = sanitize(blob)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"sanitize 过慢({elapsed:.2f}s)，疑似 ReDoS 回归"
        assert out  # 正常返回，未挂死


# ═══════════════════════════════════════════════════════
# 知识源/切片入库去重
# ═══════════════════════════════════════════════════════

class TestIngestDedup:
    def test_record_source_dedup(self, db_session):
        from app.services.knowledge import source_service
        kw = dict(project_id=1, source_type="requirement", source_id=7, title="需求X", raw_content="same body")
        s1 = source_service.record_source(db_session, **kw)
        db_session.commit()
        assert s1 is not None
        s2 = source_service.record_source(db_session, **kw)  # 同内容 → 跳过
        assert s2 is None

    def test_make_chunks_dedup(self, db_session):
        from app.services.knowledge import chunk_service, source_service
        src = source_service.record_source(
            db_session, project_id=1, source_type="manual", source_id=None,
            title="t", raw_content="body",
        )
        db_session.commit()
        n1 = chunk_service.make_chunks(db_session, src, [
            {"chunk_type": "test_case", "title": "c1", "content": "hello world"},
            {"chunk_type": "test_case", "title": "c1-dup", "content": "hello world"},  # 同内容
        ])
        db_session.commit()
        assert n1 == 1  # 去重后只入 1 条

    def test_ingest_api_test_case_builds_source(self, db_session):
        from app.models.test_case import TestCase
        from app.services.knowledge import ingest_service
        from app.models.knowledge import KnowledgeChunk, KnowledgeSource

        case = TestCase(
            project_id=1, title="matchId 缺失应返回参数错误", case_type="api",
            api_method="GET", api_endpoint="/ee/test/matchpush",
            api_assertions='[{"type":"status_code","expected":400}]',
        )
        db_session.add(case)
        db_session.commit()

        ingest_service._ingest_one_test_case(db_session, 1, case.id)
        db_session.commit()

        src = db_session.query(KnowledgeSource).filter_by(source_type="test_case", source_id=case.id).first()
        assert src is not None
        chunks = db_session.query(KnowledgeChunk).filter_by(source_id=src.id).all()
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "test_case"

    def test_ingest_skips_non_api_case(self, db_session):
        from app.models.test_case import TestCase
        from app.services.knowledge import ingest_service
        from app.models.knowledge import KnowledgeSource

        case = TestCase(project_id=1, title="功能用例", case_type="manual")
        db_session.add(case)
        db_session.commit()
        ingest_service._ingest_one_test_case(db_session, 1, case.id)
        db_session.commit()
        assert db_session.query(KnowledgeSource).filter_by(source_id=case.id).count() == 0

    def test_record_source_sanitizes_title_and_ref(self, db_session):
        """QA #2 回归：title / source_ref 入库前也必须脱敏。"""
        from app.services.knowledge import source_service
        src = source_service.record_source(
            db_session, project_id=1, source_type="test_case", source_id=55,
            title="登录 token=leaktitle",
            source_ref="GET /login?access_token=leakref",
            raw_content="body",
        )
        db_session.commit()
        assert src is not None
        assert "leaktitle" not in src.title
        assert "leakref" not in src.source_ref

    def test_record_source_supersedes_old_version(self, db_session):
        """QA #5 回归：同实体内容变更后，旧活跃源被置为 superseded，不累积僵尸。"""
        from app.services.knowledge import source_service
        from app.models.knowledge import KnowledgeSource

        s1 = source_service.record_source(
            db_session, project_id=1, source_type="test_case", source_id=77,
            title="v1", raw_content="first body",
        )
        db_session.commit()
        s2 = source_service.record_source(
            db_session, project_id=1, source_type="test_case", source_id=77,
            title="v2", raw_content="second body",  # 内容变更 → 新源
        )
        db_session.commit()
        assert s2 is not None and s2.id != s1.id
        db_session.refresh(s1)
        assert s1.status == "superseded"
        assert s2.status == "parsed"
        active = db_session.query(KnowledgeSource).filter_by(
            source_type="test_case", source_id=77, status="parsed",
        ).count()
        assert active == 1  # 仅一条活跃

    def test_supersede_cascades_chunks(self, db_session):
        """QA #5 补强：旧源被取代时其活跃切片一并置 superseded，chunk 计数不虚高。"""
        from app.services.knowledge import chunk_service, source_service
        from app.models.knowledge import KnowledgeChunk

        s1 = source_service.record_source(
            db_session, project_id=1, source_type="test_case", source_id=88,
            title="v1", raw_content="first",
        )
        chunk_service.make_chunks(db_session, s1, [
            {"chunk_type": "test_case", "title": "c", "content": "chunk-of-v1"},
        ])
        db_session.commit()
        source_service.record_source(
            db_session, project_id=1, source_type="test_case", source_id=88,
            title="v2", raw_content="second",
        )
        db_session.commit()
        old_chunks = db_session.query(KnowledgeChunk).filter_by(source_id=s1.id).all()
        assert old_chunks and all(c.status == "superseded" for c in old_chunks)
        assert db_session.query(KnowledgeChunk).filter_by(status="active").count() == 0


# ═══════════════════════════════════════════════════════
# 治理守卫：未审核不得进正式用例库
# ═══════════════════════════════════════════════════════

class TestGovernance:
    def _make_artifact(self, db_session, review_status: str):
        from app.models.knowledge import AiArtifact
        a = AiArtifact(
            project_id=1, artifact_type="test_case", title="AI 用例",
            content_json=json.dumps({
                "title": "AI 生成用例", "api_method": "POST", "api_endpoint": "/x",
            }),
            review_status=review_status,
        )
        db_session.add(a)
        db_session.commit()
        return a

    def test_import_pending_forbidden(self, db_session):
        from app.services.knowledge import artifact_service
        a = self._make_artifact(db_session, "pending")
        with pytest.raises(APIException) as ei:
            artifact_service.import_to_test_case(db_session, a.id, 1)
        assert ei.value.http_status == 403

    def test_import_approved_creates_case(self, db_session):
        from app.models.test_case import TestCase
        from app.services.knowledge import artifact_service
        a = self._make_artifact(db_session, "approved")
        result = artifact_service.import_to_test_case(db_session, a.id, 1)
        db_session.commit()
        assert result["case_id"] > 0
        case = db_session.get(TestCase, result["case_id"])
        assert case is not None and case.case_type == "api"
        db_session.refresh(a)
        assert a.review_status == "imported"
        assert a.imported_ref_id == case.id

    def test_batch_import_blocked_when_flag_off(self, db_session, monkeypatch):
        """QA #3 回归：批量导入未开启时（>1 条）应被治理门拒绝（403）。"""
        from app.core.config import settings
        from app.services.knowledge import artifact_service
        a1 = self._make_artifact(db_session, "approved")
        a2 = self._make_artifact(db_session, "approved")
        monkeypatch.setattr(settings, "ai_artifact_allow_batch_import", False, raising=False)
        with pytest.raises(APIException) as ei:
            artifact_service.import_artifacts_to_test_cases(db_session, [a1.id, a2.id], 1)
        assert ei.value.http_status == 403

    def test_batch_import_allowed_when_flag_on(self, db_session, monkeypatch):
        from app.core.config import settings
        from app.services.knowledge import artifact_service
        a1 = self._make_artifact(db_session, "approved")
        a2 = self._make_artifact(db_session, "approved")
        monkeypatch.setattr(settings, "ai_artifact_allow_batch_import", True, raising=False)
        results = artifact_service.import_artifacts_to_test_cases(db_session, [a1.id, a2.id], 1)
        db_session.commit()
        assert len(results) == 2 and all(r["case_id"] > 0 for r in results)


# ═══════════════════════════════════════════════════════
# API 访问控制 + 列表
# ═══════════════════════════════════════════════════════

class TestKnowledgeApi:
    def test_missing_permission_403(self, kdb):
        """携带有效用户但缺少 knowledge:view → 403（治理：无权不得访问）。"""
        from fastapi.testclient import TestClient

        from app.core.db import get_db
        from app.core.deps import CurrentUser, get_current_user
        from app.main import app
        from app.models.user import User

        def _override_db():
            yield kdb

        def _limited_user():
            u = User(id=2, username="viewer", password="x", nickname="V", email="v@t.local", status=1)
            # 项目成员但无 knowledge:view（用无关权限占位，避免 is_super 放行）
            return CurrentUser(user=u, permissions=["testcase:list"], project_id=1)

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _limited_user
        try:
            with TestClient(app) as c:
                resp = c.get("/api/v1/knowledge/overview")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_sources_list_shows_ingested(self, kclient, kdb):
        from app.services.knowledge import source_service
        source_service.record_source(
            kdb, project_id=1, source_type="defect", source_id=99,
            title="minis 负数导致 500", raw_content="body",
        )
        kdb.commit()

        resp = kclient.get("/api/v1/knowledge/sources")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert any(it["title"] == "minis 负数导致 500" for it in data["items"])

    def test_overview_counts(self, kclient):
        resp = kclient.get("/api/v1/knowledge/overview")
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert "source_count" in d and "health" in d
        assert "unreviewed_artifacts" in d["health"]

    def test_agent_runs_empty_ok(self, kclient):
        resp = kclient.get("/api/v1/agents/runs")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0


# ═══════════════════════════════════════════════════════
# M2 — 向量化 / 向量存储 / 混合检索
# ═══════════════════════════════════════════════════════

def _bag_vec(text: str, dim: int = 32):
    """确定性 bag-of-chars 向量（字符重叠 → 余弦相近），供离线测试替身。"""
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
    """把共享单例 embedding_service 替换为确定性替身（available/embed/embed_query/dim）。"""
    from app.services.knowledge.embedding_service import embedding_service

    monkeypatch.setattr(embedding_service, "available", lambda: True)
    monkeypatch.setattr(embedding_service, "embed", _fake_embed)
    monkeypatch.setattr(embedding_service, "embed_query", lambda q: _bag_vec(q))
    monkeypatch.setattr(embedding_service, "_model_name", "bag-test")
    monkeypatch.setattr(embedding_service, "_dim", 32)
    return embedding_service


def _seed_chunks(db, texts, project_id=1, chunk_type="test_case"):
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


class TestEmbeddingService:
    def test_empty_input_returns_none(self):
        from app.services.knowledge.embedding_service import EmbeddingService
        es = EmbeddingService()
        assert es.embed([]) is None

    def test_graceful_degradation_when_unavailable(self):
        """模型不可用（未装/下载失败）→ embed/embed_one 返回 None，绝不抛异常。"""
        from app.services.knowledge.embedding_service import EmbeddingService
        es = EmbeddingService()
        es._unavailable = True  # 模拟加载失败态
        assert es.available() is False
        assert es.embed(["x"]) is None
        assert es.embed_one("x") is None
        assert es.embed_query("x") is None


class TestVectorStore:
    def test_upsert_search_roundtrip_and_1to1(self, kdb):
        from app.services.knowledge.vector_store import SqliteVectorStore
        _seed_chunks(kdb, ["密码校验", "视频播放", "登录token"])
        from app.models.knowledge import KnowledgeChunk
        chunks = kdb.query(KnowledgeChunk).all()
        store = SqliteVectorStore()
        for c in chunks:
            store.upsert(kdb, chunk_id=c.id, project_id=1, model="bag", dim=32, vec=_bag_vec(c.content))
        kdb.commit()
        # 自身向量检索 → top-1 命中自身、score≈1
        res = store.search(kdb, project_id=1, query_vec=_bag_vec(chunks[0].content), top_k=3)
        assert res[0].chunk_id == chunks[0].id
        assert abs(res[0].score - 1.0) < 1e-4
        # 覆盖写：同 chunk_id 再 upsert 不新增行
        from app.models.knowledge import KnowledgeVector
        before = kdb.query(KnowledgeVector).count()
        store.upsert(kdb, chunk_id=chunks[0].id, project_id=1, model="bag", dim=32, vec=_bag_vec("变了"))
        kdb.commit()
        assert kdb.query(KnowledgeVector).count() == before

    def test_delete_and_project_isolation(self, kdb):
        from app.models.knowledge import KnowledgeChunk, KnowledgeVector
        from app.services.knowledge.vector_store import SqliteVectorStore
        _seed_chunks(kdb, ["a1", "b2"], project_id=1)
        _seed_chunks(kdb, ["c3"], project_id=2)
        store = SqliteVectorStore()
        for c in kdb.query(KnowledgeChunk).all():
            store.upsert(kdb, chunk_id=c.id, project_id=c.project_id, model="bag", dim=32, vec=_bag_vec(c.content))
        kdb.commit()
        # 只搜项目 1
        assert store.search(kdb, project_id=2, query_vec=_bag_vec("c3"), top_k=5)[0].score > 0.5
        # 删单个
        one = kdb.query(KnowledgeChunk).filter_by(project_id=1).first()
        assert store.delete_by_chunk(kdb, one.id) == 1
        # 项目级清空只清项目 1
        n = store.deactivate_project(kdb, 1)
        kdb.commit()
        assert n >= 1
        assert kdb.query(KnowledgeVector).filter_by(project_id=1).count() == 0
        assert kdb.query(KnowledgeVector).filter_by(project_id=2).count() == 1

    def test_dim_mismatch_skipped(self, kdb):
        """模型切换残留的异维向量在检索时被跳过，不报错。"""
        import numpy as np
        from app.models.knowledge import KnowledgeChunk, KnowledgeVector
        from app.services.knowledge.vector_store import SqliteVectorStore
        _seed_chunks(kdb, ["x"], project_id=1)
        c = kdb.query(KnowledgeChunk).first()
        # 存一个 8 维向量（与 query 的 32 维不符）
        kdb.add(KnowledgeVector(chunk_id=c.id, project_id=1, model="old", dim=8,
                                vec=np.ones(8, dtype=np.float32).tobytes()))
        kdb.commit()
        res = SqliteVectorStore().search(kdb, project_id=1, query_vec=_bag_vec("x"), top_k=3)
        assert res == []


class TestSearchService:
    def test_keyword_cjk_bigram(self, kdb, monkeypatch):
        from app.services.knowledge import search_service
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["密码字段需要非空校验", "视频清晰度切换", "支付金额校验"])
        hits = search_service.hybrid_search(kdb, project_id=1, query="密码校验", top_k=3, mode="keyword")
        assert hits and "密码" in hits[0].title + hits[0].snippet

    def test_vector_and_hybrid_modes(self, kdb, monkeypatch):
        from app.models.knowledge import KnowledgeChunk
        from app.services.knowledge import search_service, vectorize
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["密码字段需要非空校验", "视频清晰度切换", "支付金额校验"])
        vectorize._embed_and_store(kdb, kdb.query(KnowledgeChunk).all())
        kdb.commit()
        for mode in ("vector", "hybrid"):
            hits = search_service.hybrid_search(kdb, project_id=1, query="密码校验", top_k=3, mode=mode)
            assert hits, f"{mode} 应有结果"
            assert hits == sorted(hits, key=lambda h: -h.score)  # 降序

    def test_empty_query_and_isolation(self, kdb, monkeypatch):
        from app.services.knowledge import search_service
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["密码校验"], project_id=1)
        assert search_service.hybrid_search(kdb, project_id=1, query="   ", top_k=3) == []
        assert search_service.hybrid_search(kdb, project_id=999, query="密码", top_k=3) == []


class TestM2SearchApi:
    def test_search_503_when_rag_disabled(self, kclient, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        resp = kclient.post("/api/v1/knowledge/search", json={"query": "密码"})
        assert resp.status_code == 503

    def test_search_200_when_rag_enabled(self, kclient, kdb, monkeypatch):
        from app.core.config import settings
        from app.models.knowledge import KnowledgeChunk
        from app.services.knowledge import vectorize
        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        _patch_fake_embedder(monkeypatch)
        _seed_chunks(kdb, ["密码字段需要非空校验", "支付金额校验"])
        vectorize._embed_and_store(kdb, kdb.query(KnowledgeChunk).all())
        kdb.commit()
        resp = kclient.post("/api/v1/knowledge/search", json={"query": "密码校验", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list) and len(data) >= 1
        assert {"chunk_id", "snippet", "score", "source_name"} <= set(data[0].keys())

    def test_search_missing_permission_403(self, kdb):
        from fastapi.testclient import TestClient
        from app.core.config import settings
        from app.core.db import get_db
        from app.core.deps import CurrentUser, get_current_user
        from app.main import app
        from app.models.user import User

        def _override_db():
            yield kdb

        def _limited_user():
            return CurrentUser(
                user=User(id=3, username="v", password="x", nickname="V", email="v@t.local", status=1),
                permissions=["testcase:list"], project_id=1,
            )

        settings.rag_enabled = True
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _limited_user
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/knowledge/search", json={"query": "密码"})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()
            settings.rag_enabled = False

    def test_reembed_503_when_rag_disabled(self, kclient, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "rag_enabled", False, raising=False)
        resp = kclient.post("/api/v1/knowledge/reembed")
        assert resp.status_code == 503

    def test_reembed_503_when_model_unavailable(self, kclient, monkeypatch):
        from app.core.config import settings
        from app.services.knowledge.embedding_service import embedding_service
        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(embedding_service, "available", lambda: False)
        resp = kclient.post("/api/v1/knowledge/reembed")
        assert resp.status_code == 503


class TestReembedBackfillGuard:
    """回填循环健康度：零进展批次必须提前终止（评审 #21 发现的死循环隐患）。"""

    def test_no_progress_batch_terminates_not_infinite_loop(self, kdb, monkeypatch):
        """模型 available 但 embed 持续返回 None（嵌入异常/形状异常）时，embedding_id 无法回填。
        若循环不设前进守卫，同一满批切片会被反复选出 → 死循环（/reembed 同步阻塞、占用连接）。
        守卫（embedded==0 即中断）应让其在有限时间内返回 embedded=0。"""
        import threading

        from app.core.config import settings
        from app.services.knowledge import vectorize
        from app.services.knowledge.embedding_service import embedding_service

        monkeypatch.setattr(settings, "rag_enabled", True, raising=False)
        monkeypatch.setattr(embedding_service, "available", lambda: True)
        monkeypatch.setattr(embedding_service, "embed", lambda texts: None)  # 持续失败
        # 独立 Session 指向本用例的 in-memory 引擎，方能看到 seed 的切片
        monkeypatch.setattr(vectorize, "SessionLocal", lambda: kdb)
        _seed_chunks(kdb, ["密码校验", "视频播放"])  # limit==batch==2 → 老代码会死循环

        box: dict = {}

        def _run():
            box["r"] = vectorize.embed_pending_chunks_in_new_session(1, limit=2)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=5)
        assert not t.is_alive(), "回填在零进展批次上未终止（疑似死循环）"
        assert box["r"]["embedded"] == 0
        assert box["r"]["skipped"] >= 2

