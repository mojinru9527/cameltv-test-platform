"""切片 1 (VNext-1) —— 蓝湖 Provider 标准化提取 extract() 状态映射与解析。

不触网：patch lanhu_provider._extract_lanhu_content（已从 ai_service 抽离的原始函数），
断言 extract() 把返回/异常正确映射为 LanhuExtractResult.extraction_status。
"""
from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from app.services.external import lanhu_provider

_URL = "https://lanhuapp.com/web/#/item/project/detail?pid=x&docId=e6b5ce1e&versionId=26af&pageId=2b4c4235"


def _run(url=_URL):
    return asyncio.run(lanhu_provider.extract(url))


class TestParseHelpers:
    def test_pinned_runtime_without_optional_login_symbols_is_supported(self):
        module_path = str(lanhu_provider._lanhu_mcp_dir())
        sys.path.insert(0, module_path)
        try:
            runtime = lanhu_provider._load_lanhu_runtime()
        finally:
            sys.path.remove(module_path)

        assert callable(runtime.LanhuExtractor)
        assert callable(runtime.fix_html_files)
        assert runtime.auth_error_types == ()
        assert runtime.login is None
        assert runtime.save_cookie is None

    def test_pinned_extractor_without_cookie_constructor_is_supported(self):
        observed = {"created": 0}

        class Extractor:
            def __init__(self):
                observed["created"] += 1

        runtime = SimpleNamespace(LanhuExtractor=Extractor)

        instance = lanhu_provider._create_lanhu_extractor(
            runtime, "redacted-cookie",
        )

        assert isinstance(instance, Extractor)
        assert observed["created"] == 1

    def test_download_resources_supports_pinned_signature(self):
        class Extractor:
            async def download_resources(self, url, output_dir, force_update=False):
                assert force_update is False
                return {"status": "downloaded"}

        result = asyncio.run(
            lanhu_provider._download_lanhu_resources(
                Extractor(), _URL, "tmp", "version-1",
            )
        )
        assert result["status"] == "downloaded"

    def test_download_resources_preserves_newer_target_version_signature(self):
        class Extractor:
            async def download_resources(
                self, url, output_dir, target_version_id="",
            ):
                assert target_version_id == "version-1"
                return {"status": "cached"}

        result = asyncio.run(
            lanhu_provider._download_lanhu_resources(
                Extractor(), _URL, "tmp", "version-1",
            )
        )
        assert result["status"] == "cached"

    def test_download_resources_passes_page_and_safety_bounds_to_bounded_signature(self):
        class Extractor:
            async def download_resources(
                self,
                url,
                output_dir,
                force_update=False,
                *,
                target_page_id=None,
                target_version_id=None,
                max_resources=None,
                max_total_bytes=None,
                overall_timeout=None,
            ):
                assert force_update is False
                assert target_page_id == "2b4c4235"
                assert target_version_id == "version-1"
                assert max_resources == lanhu_provider._LANHU_DOWNLOAD_MAX_RESOURCES
                assert max_total_bytes == lanhu_provider._LANHU_DOWNLOAD_MAX_TOTAL_BYTES
                assert overall_timeout == lanhu_provider._LANHU_DOWNLOAD_TIMEOUT_SECONDS
                return {"status": "downloaded"}

        result = asyncio.run(
            lanhu_provider._download_lanhu_resources(
                Extractor(), _URL, "tmp", "version-1", "2b4c4235",
            )
        )
        assert result["status"] == "downloaded"

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


class TestEvidenceDownloadContract:
    @pytest.mark.parametrize(
        ("download_status", "extra"),
        [
            ("limited", {"limit_reason": "max_total_bytes"}),
            ("downloaded_with_errors", {"failed_resources": [{"path": "broken.png"}]}),
        ],
    )
    def test_incomplete_download_returns_manual_handling_status(
        self, monkeypatch, tmp_path, download_status, extra,
    ):
        class Extractor:
            def __init__(self, cookie=""):
                pass

            def parse_url(self, url):
                return {
                    "doc_id": "e6b5ce1e",
                    "version_id": "26af",
                    "page_id": "2b4c4235",
                }

            async def download_resources(
                self,
                url,
                output_dir,
                force_update=False,
                *,
                target_page_id=None,
                target_version_id=None,
                max_resources=None,
                max_total_bytes=None,
                overall_timeout=None,
            ):
                return {
                    "status": download_status,
                    "manual_action_required": True,
                    **extra,
                }

            async def get_pages_list(self, url):
                raise AssertionError("受限下载不得继续生成页面证据")

        runtime = SimpleNamespace(
            LanhuExtractor=Extractor,
            fix_html_files=lambda _: None,
            auth_error_types=(),
            login=None,
            save_cookie=None,
        )
        monkeypatch.setattr(lanhu_provider, "_load_lanhu_runtime", lambda: runtime)
        monkeypatch.setattr(lanhu_provider, "_data_dir", lambda: tmp_path)

        result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(_URL))

        assert result["status"] == "failed"
        assert result["manual_action_required"] is True
        assert "请人工处理" in result["error"]
        assert result["pages"] == []

    def test_target_page_download_exposes_local_page_for_screenshot_ocr(
        self, monkeypatch, tmp_path,
    ):
        observed: dict[str, object] = {}

        class Extractor:
            def __init__(self, cookie=""):
                pass

            def parse_url(self, url):
                return {
                    "doc_id": "e6b5ce1e",
                    "version_id": "26af",
                    "page_id": "2b4c4235",
                }

            async def download_resources(
                self,
                url,
                output_dir,
                force_update=False,
                *,
                target_page_id=None,
                target_version_id=None,
                max_resources=None,
                max_total_bytes=None,
                overall_timeout=None,
            ):
                observed["target_page_id"] = target_page_id
                path = lanhu_provider.Path(output_dir) / "target.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<html>可识别文字</html>", encoding="utf-8")
                return {"status": "downloaded"}

            async def get_pages_list(self, url):
                return {
                    "document_name": "Batch48",
                    "pages": [{
                        "id": "2b4c4235",
                        "name": "目标页",
                        "folder": "APP",
                        "filename": "target.html",
                    }],
                }

        runtime = SimpleNamespace(
            LanhuExtractor=Extractor,
            fix_html_files=lambda _: None,
            auth_error_types=(),
            login=None,
            save_cookie=None,
        )
        monkeypatch.setattr(lanhu_provider, "_load_lanhu_runtime", lambda: runtime)
        monkeypatch.setattr(lanhu_provider, "_data_dir", lambda: tmp_path)

        result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(_URL))

        assert result["status"] == "success"
        assert observed["target_page_id"] == "2b4c4235"
        assert result["pages"][0]["id"] == "2b4c4235"
        assert result["pages"][0]["local_url"].startswith("file:")


def test_delegation_identity():
    """ai_service 委托到 provider 的同一函数（抽取+委托，保行为）。"""
    from app.services import ai_service
    assert ai_service._extract_lanhu_content is lanhu_provider._extract_lanhu_content
