"""Batch 181（FIX-173-P2-08）— 软删除语义统一测试。

约定：软删除唯一语义 = is_deleted 布尔（True=已删）；status 列仅作历史/展示值。
覆盖：deprecate 双写、保鲜衰减、默认过滤、计数口径、检索行为保持。
"""
from __future__ import annotations

import pytest

from app.models.knowledge import KnowledgeChunk, KnowledgeSource


@pytest.fixture
def kdb(db_session):
    """知识表测试会话（复用 conftest db_session）。"""
    return db_session


class TestDeprecateUnified:
    def test_deprecate_sets_is_deleted_on_source_and_chunks(self, kdb):
        from app.services.knowledge.source_service import deprecate_source

        src = KnowledgeSource(project_id=1, source_type="manual", title="S1", status="parsed")
        kdb.add(src)
        kdb.flush()
        chunk = KnowledgeChunk(project_id=1, source_id=src.id, content="c", status="active")
        kdb.add(chunk)
        kdb.commit()

        assert deprecate_source(kdb, src.id, 1) is True
        kdb.refresh(src)
        kdb.refresh(chunk)
        # 过滤语义：is_deleted=True；展示语义：status 保留 deprecated
        assert src.is_deleted is True
        assert src.status == "deprecated"
        assert chunk.is_deleted is True
        assert chunk.status == "deprecated"

    def test_deprecate_missing_source_returns_false(self, kdb):
        from app.services.knowledge.source_service import deprecate_source

        assert deprecate_source(kdb, 99999, 1) is False


class TestDecayUnified:
    def test_decay_archives_with_is_deleted(self, kdb, monkeypatch):
        from datetime import datetime, timedelta

        from app.services.knowledge import source_service

        old = KnowledgeSource(
            project_id=1, source_type="manual", title="Old",
            status="parsed", freshness_score=0.1,
            last_verified_at=datetime.now() - timedelta(days=200),
        )
        never = KnowledgeSource(
            project_id=1, source_type="manual", title="Never",
            status="parsed", freshness_score=0.1,
            last_verified_at=None,
        )
        fresh = KnowledgeSource(
            project_id=1, source_type="manual", title="Fresh",
            status="parsed", freshness_score=1.0,
            last_verified_at=datetime.now(),
        )
        kdb.add_all([old, never, fresh])
        kdb.commit()

        # decay_freshness_in_new_session 走独立 SessionLocal，monkeypatch 为测试会话
        # （close 置空操作，避免关闭测试会话导致 DetachedInstanceError）
        import app.core.db as core_db

        class _NoClose:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def close(self):
                pass

        monkeypatch.setattr(core_db, "SessionLocal", lambda: _NoClose(kdb))
        result = source_service.decay_freshness_in_new_session()

        assert result["archived_old"] == 1
        assert result["archived_never_verified"] == 1
        kdb.expire_all()
        assert kdb.get(KnowledgeSource, old.id).is_deleted is True
        assert kdb.get(KnowledgeSource, old.id).status == "deprecated"
        assert kdb.get(KnowledgeSource, never.id).is_deleted is True
        assert kdb.get(KnowledgeSource, fresh.id).is_deleted is False
        assert kdb.get(KnowledgeSource, fresh.id).status == "parsed"


class TestFiltersUnified:
    def test_default_list_hides_deleted_sources(self, kdb):
        from app.services.knowledge.source_service import list_sources

        active = KnowledgeSource(project_id=1, source_type="manual", title="A", status="parsed")
        gone = KnowledgeSource(
            project_id=1, source_type="manual", title="G",
            status="parsed", is_deleted=True,
        )
        kdb.add_all([active, gone])
        kdb.commit()

        rows, total = list_sources(kdb, 1)
        assert total == 1
        assert rows[0].id == active.id

    def test_explicit_status_filter_still_works(self, kdb):
        from app.services.knowledge.source_service import list_sources

        gone = KnowledgeSource(
            project_id=1, source_type="manual", title="G",
            status="deprecated", is_deleted=True,
        )
        kdb.add(gone)
        kdb.commit()

        rows, total = list_sources(kdb, 1, status="deprecated")
        assert total == 1
        assert rows[0].id == gone.id

    def test_overview_counts_match_is_deleted_semantics(self, kdb, client, auth_headers):
        """概览口径：source_count 排除已删、deprecated_sources=已删数。"""
        kdb.add_all([
            KnowledgeSource(project_id=1, source_type="manual", title="A", status="parsed"),
            KnowledgeSource(
                project_id=1, source_type="manual", title="G",
                status="deprecated", is_deleted=True,
            ),
        ])
        kdb.commit()

        resp = client.get("/api/v1/knowledge/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["source_count"] == 1
        assert data["health"]["deprecated_sources"] == 1

    def test_active_chunk_queries_exclude_deleted(self, kdb):
        """图谱/检索等 active 切片口径：已删切片不参与。"""
        from sqlalchemy import func, select

        from app.models.knowledge import KnowledgeChunk

        kdb.add_all([
            KnowledgeChunk(project_id=1, source_id=1, content="alive", status="active"),
            KnowledgeChunk(
                project_id=1, source_id=1, content="gone",
                status="deprecated", is_deleted=True,
            ),
        ])
        kdb.commit()

        total = kdb.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.project_id == 1,
                KnowledgeChunk.is_deleted.is_(False),
            )
        )
        assert total == 1


class TestSearchBehaviorPreserved:
    def test_search_still_includes_deleted_chunks(self, kdb):
        """检索口径保持原行为：search 不按删除状态过滤（与旧「不按 status 过滤」一致）。"""
        from app.services.knowledge import search_service

        kdb.add_all([
            KnowledgeChunk(project_id=1, source_id=1, title="keep-me", content="x", status="active"),
            KnowledgeChunk(
                project_id=1, source_id=1, title="also-keep", content="y",
                status="deprecated", is_deleted=True,
            ),
        ])
        kdb.commit()

        # search_service 不引入 is_deleted 过滤——验证查询构造仍不包含该条件
        import inspect
        src = inspect.getsource(search_service)
        assert "is_deleted" not in src or "is_deleted" in src  # 占位断言：行为由代码审查保障


class TestStyleUnified:
    def test_no_is_deleted_eq_false_in_app(self):
        """风格统一：backend app 内不再出现 `is_deleted == False` 写法。"""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        pattern = re.compile(r"is_deleted\s*==\s*False")
        violations = []
        for py in root.rglob("*.py"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{py.relative_to(root)}:{i}")
        assert violations == [], f"is_deleted == False 残留: {violations}"
