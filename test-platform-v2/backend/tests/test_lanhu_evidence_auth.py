"""Batch 133 — 蓝湖证据采集会话失效（418）识别与失败状态修复测试。"""
from __future__ import annotations

import asyncio
import httpx
import pytest
from types import SimpleNamespace

from app.services.external import lanhu_provider
from app.services.external.lanhu_provider import (
    _is_lanhu_session_expired,
    clear_lanhu_cookie,
    get_lanhu_cookie,
    set_lanhu_cookie,
)


def _http_418() -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://lanhuapp.com/api/project/image")
    resp = httpx.Response(418, request=req)
    return httpx.HTTPStatusError("Client error '418 Unknown'", request=req, response=resp)


class TestSessionExpiredClassification:
    def test_418_is_session_expired(self):
        assert _is_lanhu_session_expired(_http_418()) is True

    def test_401_and_403_are_session_expired(self):
        for status in (401, 403):
            req = httpx.Request("GET", "https://lanhuapp.com/api/project/image")
            resp = httpx.Response(status, request=req)
            err = httpx.HTTPStatusError("err", request=req, response=resp)
            assert _is_lanhu_session_expired(err) is True

    def test_500_is_not_session_expired(self):
        req = httpx.Request("GET", "https://lanhuapp.com/x")
        resp = httpx.Response(500, request=req)
        err = httpx.HTTPStatusError("err", request=req, response=resp)
        assert _is_lanhu_session_expired(err) is False

    def test_non_http_error_is_not_session_expired(self):
        assert _is_lanhu_session_expired(ValueError("boom")) is False


class TestCookieStore:
    def test_set_get_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lanhu_provider.settings, "data_dir", str(tmp_path))
        set_lanhu_cookie("abc=123; lanhu_session=xyz")
        assert get_lanhu_cookie() == "abc=123; lanhu_session=xyz"
        clear_lanhu_cookie()
        assert get_lanhu_cookie() == ""

    def test_rejects_empty_or_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lanhu_provider.settings, "data_dir", str(tmp_path))
        with pytest.raises(ValueError):
            set_lanhu_cookie("")
        with pytest.raises(ValueError):
            set_lanhu_cookie("your_lanhu_cookie_here")


class TestEvidenceFlowSessionFailure:
    def test_get_lanhu_pages_returns_session_error_not_raw_418(self, monkeypatch, tmp_path):
        """418 应转为"会话失效 + manual_action_required"明确失败，而非原样 418。"""
        class _Extractor:
            def __init__(self, cookie=""):
                pass

            def parse_url(self, url):
                return {"doc_id": "doc-1", "project_id": "p1", "team_id": "t1", "version_id": "v1", "page_id": ""}

            async def download_resources(self, url, out_dir, **kwargs):
                return {"status": "downloaded"}

            async def get_pages_list(self, url):
                raise _http_418()

        runtime = SimpleNamespace(
            LanhuExtractor=_Extractor,
            fix_html_files=lambda d: None,
            auth_error_types=(),
            login=None,
            save_cookie=None,
        )
        monkeypatch.setattr(lanhu_provider, "_load_lanhu_runtime", lambda: runtime)
        monkeypatch.setattr(lanhu_provider.settings, "data_dir", str(tmp_path))

        result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(
            "https://lanhuapp.com/web/#/item/project/product?tid=t1&pid=p1&docId=doc-1&versionId=v1"
        ))
        assert result["status"] == "failed"
        assert result.get("manual_action_required") is True
        assert "会话" in result["error"] or "418" in result["error"]


class TestAiServiceDoesNotSwallowSessionError:
    def test_session_error_is_not_folded_into_image_format_fallback(self, monkeypatch):
        from types import SimpleNamespace

        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "ai_api_key", "test-key")
        # A2：项目级 AI 配置 —— 打桩 resolve（成功，让流程走到 lanhu 分支）
        monkeypatch.setattr(
            ai_service.ai_config_service,
            "resolve",
            lambda db, project_id: SimpleNamespace(
                api_base_url="https://api.deepseek.com",
                api_key="sk-test",
                model="deepseek-v4-pro",
            ),
        )

        async def _raise_session(url, auto_login=True):
            raise ValueError("蓝湖认证失败，Cookie 已过期或已被拒绝（HTTP 418 表示会话失效）")

        monkeypatch.setattr(ai_service, "_extract_lanhu_content", _raise_session)
        # 旧逻辑会把任何 ValueError 当作"图片格式"兜底；新逻辑必须透传会话失效
        with pytest.raises(ValueError) as excinfo:
            asyncio.run(ai_service.extract_features(
                None,
                1,
                content="补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字补充说明文字",
                file_type="lanhu",
                source_ref="https://lanhuapp.com/web/#/item/project/product?tid=t1&pid=p1&docId=doc-1",
            ))
        assert "会话" in str(excinfo.value) or "Cookie" in str(excinfo.value)
