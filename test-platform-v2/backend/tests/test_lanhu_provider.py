"""切片 1 (VNext-1) —— 蓝湖 Provider 标准化提取 extract() 状态映射与解析。

不触网：patch lanhu_provider._extract_lanhu_content（已从 ai_service 抽离的原始函数），
断言 extract() 把返回/异常正确映射为 LanhuExtractResult.extraction_status。
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.external import lanhu_provider

_URL = "https://lanhuapp.com/web/#/item/project/detail?pid=x&docId=e6b5ce1e&versionId=26af&pageId=2b4c4235"


def _run(url=_URL):
    return asyncio.run(lanhu_provider.extract(url))


class TestParseHelpers:
    def test_parse_url_ids(self):
        doc, ver, page = lanhu_provider._parse_url_ids(_URL)
        assert doc == "e6b5ce1e" and ver == "26af" and page == "2b4c4235"

    def test_parse_url_ids_missing(self):
        assert lanhu_provider._parse_url_ids("https://lanhuapp.com/web/#/item/project/board") == ("", "", "")

    def test_classify_error_status(self):
        assert lanhu_provider._classify_error_status("蓝湖登录态已失效，请配置 LANHU_COOKIE") == "auth_failed"
        assert lanhu_provider._classify_error_status("无权访问该项目，请联系管理员开权限") == "permission_denied"
        assert lanhu_provider._classify_error_status("原型为图片，请在补充说明中描述") == "image_only"
        assert lanhu_provider._classify_error_status("请提交具体文档链接（缺少 docId）") == "invalid_url"
        assert lanhu_provider._classify_error_status("something exploded") == "failed"


class TestExtractStatus:
    def test_invalid_url_short_circuit(self):
        r = asyncio.run(lanhu_provider.extract("https://lanhuapp.com/web/#/item/project/board"))
        assert r.extraction_status == "invalid_url"

    def test_success(self, monkeypatch):
        async def _fake(url, auto_login=True):
            return {"content": "比赛推送\nmatchId 必填\n当比赛进行到指定分钟推送",
                    "page_filtered": True, "folder_name": "赛事模块",
                    "changelog": {"raw": "v1.2 新增比赛推送"}, "client_scope": ["app", "pc"]}
        monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
        r = _run()
        assert r.extraction_status == "success"
        assert r.module_name == "赛事模块"
        assert r.client_scope == ["app", "pc"]
        assert r.content_hash  # 有内容 → 有 hash
        assert r.immutable_version == "lanhu:e6b5ce1e:26af:2b4c4235"
        assert "比赛推送" in r.content_md

    def test_image_only_when_empty_content(self, monkeypatch):
        async def _fake(url, auto_login=True):
            return {"content": "   ", "page_filtered": False, "folder_name": "",
                    "changelog": None, "client_scope": []}
        monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
        r = _run()
        assert r.extraction_status == "image_only"

    def test_auth_failed_from_valueerror(self, monkeypatch):
        async def _fake(url, auto_login=True):
            raise ValueError("蓝湖登录态失效，请设置 LANHU_USERNAME/LANHU_PASSWORD")
        monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
        r = _run()
        assert r.extraction_status == "auth_failed"
        assert "LANHU" in r.extraction_summary

    def test_failed_never_raises(self, monkeypatch):
        async def _fake(url, auto_login=True):
            raise RuntimeError("boom")
        monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
        r = _run()  # 不抛异常
        assert r.extraction_status == "failed"


def test_delegation_identity():
    """ai_service 委托到 provider 的同一函数（抽取+委托，保行为）。"""
    from app.services import ai_service
    assert ai_service._extract_lanhu_content is lanhu_provider._extract_lanhu_content
