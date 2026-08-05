"""切片 1 (VNext-1) —— 蓝湖 Provider 标准化提取 extract() 状态映射与解析。

不触网：patch lanhu_provider._extract_lanhu_content（已从 ai_service 抽离的原始函数），
断言 extract() 把返回/异常正确映射为 LanhuExtractResult.extraction_status。
"""
from __future__ import annotations

import asyncio
import re
import sys
from types import SimpleNamespace

import pytest


from app.services.external import lanhu_provider

_URL = "https://lanhuapp.com/web/#/item/project/detail?pid=x&docId=e6b5ce1e&versionId=26af&pageId=2b4c4235"


def _run(url=_URL):
    return asyncio.run(lanhu_provider.extract(url))


class TestParseHelpers:
    def test_backend_declares_all_pinned_lanhu_runtime_dependencies(self):
        def requirement_names(path):
            names = set()
            for line in path.read_text(encoding="utf-8").splitlines():
                requirement = line.split("#", 1)[0].strip()
                if not requirement or requirement.startswith("-"):
                    continue
                name = re.split(r"[<>=!~\[\]\s]", requirement, maxsplit=1)[0]
                names.add(name.lower().replace("_", "-"))
            return names

        workspace_root = lanhu_provider._resolve_workspace_root()
        backend_requirements = requirement_names(
            workspace_root / "test-platform-v2" / "backend" / "requirements.txt"
        )
        lanhu_requirements = requirement_names(
            lanhu_provider._lanhu_mcp_dir() / "requirements.txt"
        )

        assert lanhu_requirements <= backend_requirements

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


# ═══════════════════════════════════════════════════════
# C87-1 项目级蓝湖链接（仅 tid+pid，无 docId）→ 自动发现文档
# ═══════════════════════════════════════════════════════

_PROJECT_URL = (
    "https://lanhuapp.com/web/#/item/project/stage"
    "?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1"
    "&pid=c92eba63-69eb-4123-97c0-6605ce2e3216"
)


class _FakeProjectExtractor:
    """项目级 URL 提取器 mock：parse_url 按是否带 docId 返回不同结果。"""

    def __init__(self, cookie="", images=None, http_error=False):
        self.images = images if images is not None else [
            {"id": "doc-web-001", "name": "Web 端设计稿"},
        ]
        self.http_error = http_error
        self.downloaded_doc_id: str | None = None

    def parse_url(self, url):
        if "docId=" in url:
            return {
                "doc_id": "doc-web-001",
                "version_id": "",
                "page_id": "",
                "team_id": "6324825d-1614-4d73-bc4c-f05cdf0734c1",
                "project_id": "c92eba63-69eb-4123-97c0-6605ce2e3216",
            }
        return {
            "doc_id": "",
            "version_id": "",
            "page_id": "",
            "team_id": "6324825d-1614-4d73-bc4c-f05cdf0734c1",
            "project_id": "c92eba63-69eb-4123-97c0-6605ce2e3216",
        }

    async def _project_images(self, url):
        if self.http_error:
            return SimpleNamespace(status_code=500, json=lambda: {})
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "code": "00000",
                "data": {"images": self.images},
            },
        )

    @property
    def client(self):
        return SimpleNamespace(get=self._project_images)

    async def download_resources(self, url, output_dir, **kwargs):
        self.downloaded_doc_id = "doc-web-001" if "docId=" in url else ""
        return {"status": "downloaded"}

    async def get_pages_list(self, url):
        return {
            "document_name": "Web 端设计稿",
            "pages": [{
                "id": "p1",
                "name": "登录页",
                "folder": "Web",
                "filename": "login.html",
            }],
        }


def _with_runtime(extractor, url: str) -> dict:
    """以注入 runtime 的方式调用 get_lanhu_pages_for_evidence（不触网）。"""
    import asyncio as _asyncio

    return _asyncio.run(_call_with_runtime(extractor, url))


async def _call_with_runtime(extractor, url: str) -> dict:
    monkeypatch = None
    # 直接注入：临时替换 _load_lanhu_runtime
    import app.services.external.lanhu_provider as _lp

    runtime = SimpleNamespace(
        LanhuExtractor=lambda cookie="": extractor,
        fix_html_files=lambda _: None,
        auth_error_types=(),
        login=None,
        save_cookie=None,
    )
    original = _lp._load_lanhu_runtime
    _lp._load_lanhu_runtime = lambda: runtime
    try:
        return await _lp.get_lanhu_pages_for_evidence(url)
    finally:
        _lp._load_lanhu_runtime = original


class TestProjectUrlEvidence:
    def test_project_url_auto_discovers_first_doc_and_returns_pages(self):
        """项目级链接（无 docId）→ 自动发现首个文档并返回页面证据。"""
        extractor = _FakeProjectExtractor()
        result = _with_runtime(extractor, _PROJECT_URL)

        assert result["status"] == "success"
        assert extractor.downloaded_doc_id == "doc-web-001"
        assert result["document_name"] == "Web 端设计稿"
        assert result["pages"] and result["pages"][0]["id"] == "p1"

    def test_project_url_empty_images_returns_failed_with_clear_error(self):
        """项目内无设计文档 → failed（提示未发现设计文档，而非缺少 docId）。"""
        extractor = _FakeProjectExtractor(images=[])
        result = _with_runtime(extractor, _PROJECT_URL)

        assert result["status"] == "failed"
        assert "设计文档" in result["error"]
        assert "缺少 docId" not in result["error"]

    def test_project_url_http_error_returns_failed_without_crash(self):
        """项目文档列表接口异常 → failed，不裸抛。"""
        extractor = _FakeProjectExtractor(http_error=True)
        result = _with_runtime(extractor, _PROJECT_URL)

        assert result["status"] == "failed"
        assert result["pages"] == []

    def test_shared_helper_resolves_first_doc(self):
        """共享 helper _resolve_project_doc 返回追加 docId 的 URL 与 doc_id。"""
        extractor = _FakeProjectExtractor()

        effective_url, doc_id = asyncio.run(
            lanhu_provider._resolve_project_doc(_PROJECT_URL, extractor)
        )

        assert doc_id == "doc-web-001"
        assert "docId=doc-web-001" in effective_url

    def test_shared_helper_raises_when_project_has_no_docs(self):
        """共享 helper 在项目内无设计文档时给出明确错误。"""
        extractor = _FakeProjectExtractor(images=[])

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(lanhu_provider._resolve_project_doc(_PROJECT_URL, extractor))

        assert "设计文档" in str(exc_info.value)


class _FakeBoardExtractor:
    """设计图板项目 mock：/api/project/images 返回图+批注卡，图片 URL 可下载。"""

    def __init__(self, cookie="", images=None, http_error=False):
        self.images = images if images is not None else [
            {"id": "img-1", "name": "首页", "type": "image",
             "url": "https://cdn.example/img1.png"},
            {"id": "img-2", "name": "详情页", "type": "image",
             "url": "https://cdn.example/img2.png"},
            {"id": "card-1", "name": "金额高度 64px 改 68px", "type": "card", "url": ""},
        ]
        self.http_error = http_error
        self.downloaded = []

    def parse_url(self, url):
        return {
            "doc_id": None,
            "version_id": None,
            "page_id": "",
            "team_id": "6324825d-1614-4d73-bc4c-f05cdf0734c1",
            "project_id": "c92eba63-69eb-4123-97c0-6605ce2e3216",
        }

    async def _get(self, url):
        url_str = str(url)
        if url_str.startswith("https://cdn.example/"):
            self.downloaded.append(url_str)
            return SimpleNamespace(
                status_code=200,
                content=b"\x89PNG\r\n\x1a\n" + b"0" * 32,
            )
        if self.http_error:
            return SimpleNamespace(status_code=500, json=lambda: {})
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"code": "00000", "data": {"images": self.images}},
        )

    @property
    def client(self):
        return SimpleNamespace(get=self._get)

    async def download_resources(self, url, output_dir, **kwargs):
        raise AssertionError("设计图板流程不应走文档下载")

    async def get_pages_list(self, url):
        raise AssertionError("设计图板流程不应走页面列表")


class TestDesignBoardEvidence:
    def test_project_url_captures_images_and_cards_as_pages(self, tmp_path):
        """项目级链接（设计图板）→ 图片原图 + 批注卡 HTML 页面。"""
        extractor = _FakeBoardExtractor()

        async def run():
            return await lanhu_provider._get_design_board_pages(
                _PROJECT_URL, extractor, str(tmp_path),
            )

        board = asyncio.run(run())
        assert board is not None
        assert board["status"] == "success"
        assert board["document_name"] == "蓝湖设计图板"
        assert len(board["pages"]) == 3

        image_pages = [p for p in board["pages"] if p["folder"] == "设计图板"]
        card_pages = [p for p in board["pages"] if p["folder"] == "设计批注"]
        assert len(image_pages) == 2
        assert len(card_pages) == 1
        assert image_pages[0]["local_url"].startswith("file:")
        assert image_pages[0]["local_url"].endswith(".png")
        assert card_pages[0]["local_url"].endswith(".html")
        assert len(extractor.downloaded) == 2

    def test_board_url_with_no_images_falls_back_to_doc_discovery(self, tmp_path):
        """项目内无设计图（images 空）→ 图板分支让位，错误指向设计文档。"""
        extractor = _FakeBoardExtractor(images=[])
        runtime = SimpleNamespace(
            LanhuExtractor=lambda cookie="": extractor,
            fix_html_files=lambda _: None,
            auth_error_types=(),
            login=None,
            save_cookie=None,
        )
        original = lanhu_provider._load_lanhu_runtime
        lanhu_provider._load_lanhu_runtime = lambda: runtime
        try:
            result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(_PROJECT_URL))
        finally:
            lanhu_provider._load_lanhu_runtime = original

        assert result["status"] == "failed"
        assert "设计文档" in result["error"]

    def test_board_http_error_returns_none(self, tmp_path):
        """images 接口异常 → 图板分支返回 None（不崩）。"""
        extractor = _FakeBoardExtractor(http_error=True)

        async def run():
            return await lanhu_provider._get_design_board_pages(
                _PROJECT_URL, extractor, str(tmp_path),
            )

        assert asyncio.run(run()) is None
