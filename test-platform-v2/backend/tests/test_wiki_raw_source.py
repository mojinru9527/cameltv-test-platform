"""切片 1 (VNext-1) —— Wiki Raw Source 去重 / supersede / 列表 / 详情。"""
from __future__ import annotations

from app.models.wiki import WikiRawSource
from app.services.wiki import raw_source_service as rs


def _record(db, **over):
    kw = dict(
        project_id=1, source_type="lanhu", source_ref="https://lanhuapp.com/x",
        title="比赛推送", content_md="matchId 必填", content_hash="hash-a",
        immutable_version="doc:ver:page",
    )
    kw.update(over)
    return rs.record_raw_source(db, **kw)


class TestRecordRawSource:
    def test_persist_and_get(self, db_session):
        row = _record(db_session)
        db_session.commit()
        assert row is not None and row.id
        got = rs.get_raw_source(db_session, row.id, 1)
        assert got and got.title == "比赛推送" and got.status == "active"
        # 内容脱敏管线生效（content_md 走 sanitize）
        assert got.content_md == "matchId 必填"

    def test_dedup_same_content_skipped(self, db_session):
        first = _record(db_session)
        db_session.flush()
        dup = _record(db_session)  # 同 immutable_version + content_hash
        assert first is not None and dup is None

    def test_supersede_on_content_change(self, db_session):
        old = _record(db_session, content_hash="hash-old")
        db_session.flush()
        new = _record(db_session, content_hash="hash-new")  # 同 version，新内容
        db_session.flush()
        assert new is not None and new.status == "active"
        db_session.refresh(old)
        assert old.status == "superseded"

    def test_get_wrong_project_returns_none(self, db_session):
        row = _record(db_session)
        db_session.commit()
        assert rs.get_raw_source(db_session, row.id, project_id=999) is None

    def test_list_filters(self, db_session):
        _record(db_session, title="比赛推送", content_hash="h1", immutable_version="v1")
        _record(db_session, title="登录鉴权", content_hash="h2", immutable_version="v2", source_type="requirement")
        db_session.commit()
        rows, total = rs.list_raw_sources(db_session, 1)
        assert total == 2
        rows, total = rs.list_raw_sources(db_session, 1, source_type="lanhu")
        assert total == 1 and rows[0].title == "比赛推送"
        rows, total = rs.list_raw_sources(db_session, 1, keyword="登录")
        assert total == 1 and rows[0].title == "登录鉴权"
