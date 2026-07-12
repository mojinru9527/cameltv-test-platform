"""切片 2 (VNext-2) —— Wiki 两阶段编译：分析(mock LLM) + 确定性生成 + 页面版本化。"""
from __future__ import annotations

import json

from app.models.wiki import WikiLink, WikiPage, WikiRawSource
from app.services.wiki import ingest_service, page_service


_ANALYSIS = {
    "source_summary": "赛事模块比赛推送需求",
    "detected_modules": ["赛事模块"],
    "requirements": [{
        "stable_key": "lanhu:e6b5ce1e:2b4c4235:match_push",
        "title": "比赛推送", "module": "赛事模块",
        "description": "当比赛进行到指定分钟推送提醒",
        "client_scope": ["app"],
        "business_rules": [{"id": "R1", "rule": "matchId 必填", "evidence": "页面出现 matchId"}],
        "fields": [{"name": "matchId", "location": "query", "type": "string", "required": True}],
        "apis": [{"method": "GET", "path": "/ee/test/matchpush"}],
        "test_focus": ["matchId 边界"],
    }],
    "connections": [{"from": "比赛推送", "to": "赛事模块", "type": "mentions", "evidence": "同模块"}],
    "review_items": [{"title": "端范围不明确", "reason": "未标注 PC", "confidence": 0.4}],
    "confidence": 0.8,
}


def _raw(db):
    row = WikiRawSource(
        project_id=1, source_type="lanhu", source_ref="https://lanhuapp.com/x",
        title="比赛推送", content_md="比赛推送\nmatchId 必填", content_hash="h1",
        immutable_version="e6b5ce1e:26af:2b4c4235", knowledge_source_id=42,
        metadata_json=json.dumps({"client_scope": ["app"]}, ensure_ascii=False),
    )
    db.add(row); db.flush()
    return row


class TestAnalysis:
    def test_uses_llm_result(self, monkeypatch, db_session):
        monkeypatch.setattr(ingest_service, "_call_llm_sync",
                            lambda *a, **k: {"result": _ANALYSIS, "raw": "", "error": None})
        out = ingest_service._run_analysis(_raw(db_session))
        assert out["requirements"][0]["title"] == "比赛推送"
        assert not out.get("_fallback")

    def test_fallback_when_llm_unavailable(self, monkeypatch, db_session):
        monkeypatch.setattr(ingest_service, "_call_llm_sync",
                            lambda *a, **k: {"result": None, "raw": "", "error": "AI_API_KEY 未配置"})
        out = ingest_service._run_analysis(_raw(db_session))
        assert out.get("_fallback") is True
        assert out["requirements"] and out["requirements"][0]["title"] == "比赛推送"


class TestGeneration:
    def test_generates_pages_links_with_source_refs(self, db_session):
        raw = _raw(db_session)
        result = ingest_service._generate(db_session, 1, raw, _ANALYSIS)
        db_session.flush()
        pages = db_session.query(WikiPage).filter_by(project_id=1).all()
        types = {p.page_type for p in pages}
        assert {"source", "module", "requirement", "rule", "index"} <= types
        # 每页都有来源引用
        for p in pages:
            assert json.loads(p.source_refs_json), f"page {p.slug} missing source_refs"
        # 需求页引用 raw source id
        req = next(p for p in pages if p.page_type == "requirement")
        assert json.loads(req.source_refs_json)[0]["raw_source_id"] == raw.id
        # 页面链接：来源→需求(source_of) + 需求→规则(covers)
        links = db_session.query(WikiLink).filter_by(project_id=1).all()
        assert any(l.link_type == "source_of" for l in links)
        assert any(l.link_type == "covers" for l in links)
        assert result["pages"] >= 5

    def test_generated_pages_pending_by_default(self, db_session):
        raw = _raw(db_session)
        ingest_service._generate(db_session, 1, raw, _ANALYSIS)
        db_session.flush()
        assert all(p.review_status == "pending"
                   for p in db_session.query(WikiPage).filter_by(project_id=1).all())


class TestPageVersioning:
    def test_approved_page_not_overwritten(self, db_session):
        p1 = page_service.upsert_page(db_session, project_id=1, page_type="requirement",
                                      slug="match-push", title="比赛推送", content_md="v1 内容")
        db_session.flush()
        page_service.review_page(db_session, p1.id, 1, approve=True)
        db_session.flush()
        # 同 slug 新内容 → 不覆盖 approved，旧版 superseded + 新 pending v2
        p2 = page_service.upsert_page(db_session, project_id=1, page_type="requirement",
                                      slug="match-push", title="比赛推送", content_md="v2 内容")
        db_session.flush()
        db_session.refresh(p1)
        assert p1.review_status == "superseded" and p1.content_md == "v1 内容"
        assert p2.id != p1.id and p2.version == 2 and p2.review_status == "pending"

    def test_same_content_no_new_version(self, db_session):
        a = page_service.upsert_page(db_session, project_id=1, page_type="module",
                                     slug="m", title="M", content_md="same")
        db_session.flush()
        b = page_service.upsert_page(db_session, project_id=1, page_type="module",
                                     slug="m", title="M", content_md="same")
        assert a.id == b.id and b.version == 1
