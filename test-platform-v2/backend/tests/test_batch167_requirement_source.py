"""Batch 167 Phase 1 — 需求源适配与提取完整度回归。"""
from __future__ import annotations

import json

import httpx
import pytest

from app.models.requirement import RequirementDocument
from app.services import ai_service
from app.services.requirement_source_service import (
    RequirementSourceError,
    _html_to_text,
    classify_url,
    fetch_url_content,
)


class TestUrlClassification:
    def test_classify_kinds(self):
        assert classify_url("https://lanhuapp.com/x") == "lanhu"
        assert classify_url("https://x.pingcode.com/story/1") == "pingcode"
        assert classify_url("https://example.atlassian.net/wiki/spaces/A/pages/1") == "confluence"
        assert classify_url("https://example.com/req.html") == "generic"

    def test_invalid_url(self):
        with pytest.raises(RequirementSourceError):
            classify_url("")


class TestHtmlToText:
    def test_strips_script_and_keeps_text(self):
        html = "<html><head><title>T</title><script>var a=1;</script></head><body><h1>标题</h1><p>正文内容</p></body></html>"
        text = _html_to_text(html)
        assert "标题" in text
        assert "正文内容" in text
        assert "var a=1" not in text


class TestGenericFetch:
    def test_fetch_html(self, monkeypatch):
        def fake_get(url, headers=None, timeout=None, follow_redirects=True):
            return httpx.Response(200, text="<html><head><title>需求标题</title></head><body><p>正文</p></body></html>")
        monkeypatch.setattr(httpx, "get", fake_get)
        result = fetch_url_content("https://example.com/req.html")
        assert "正文" in result["content"]
        assert result["title"] == "需求标题"
        assert result["kind"] == "generic"

    def test_lanhu_fails_closed(self):
        with pytest.raises(RequirementSourceError):
            fetch_url_content("https://lanhuapp.com/x")


class TestChunkExtractionHelpers:
    def test_split_large_content(self):
        content = "\n\n".join(f"段落 {i} " + "x" * 500 for i in range(200))
        chunks = ai_service._split_content_chunks(content)
        assert len(chunks) > 1
        assert max(len(c) for c in chunks) <= 26000

    def test_merge_dedupes_modules_and_fps(self):
        results = [
            {"modules": [{"name": "首页", "function_points": [{"title": "直播列表加载"}]}], "overall_assessment": "A"},
            {"modules": [{"name": "首页", "function_points": [{"title": "直播列表加载"}, {"title": "广告位展示"}]}], "overall_assessment": "B"},
        ]
        merged = ai_service._merge_extractions(results)
        assert len(merged["modules"]) == 1
        fps = merged["modules"][0]["function_points"]
        assert len(fps) == 2
        assert {fp["title"] for fp in fps} == {"直播列表加载", "广告位展示"}


class TestSourceUrlUpload:
    def test_upload_from_source_url(self, db_session, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.requirement_source_service.fetch_url_content",
            lambda url, kind=None: {"content": "测试需求正文", "kind": "generic", "title": "在线需求"},
        )
        resp = client.post(
            "/api/v1/requirements/upload",
            data={"source_url": "https://example.com/req.html"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["file_type"] == "generic"
        assert data["source_ref"] == "https://example.com/req.html"


class TestExtractionQualityEndpoint:
    def test_quality_reads_meta(self, db_session, client, auth_headers):
        doc = RequirementDocument(
            project_id=1, title="B167-Q", status="uploaded",
            extraction_meta=json.dumps({"mode": "chunked", "chunks": 3, "fallback": True, "module_count": 4, "function_point_count": 40, "warnings": ["w1"]}),
        )
        db_session.add(doc)
        db_session.commit()
        resp = client.get(f"/api/v1/requirements/{doc.id}/extraction-quality", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mode"] == "chunked"
        assert data["chunks"] == 3
        assert data["fallback"] is True
        assert data["function_point_count"] == 40


