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
