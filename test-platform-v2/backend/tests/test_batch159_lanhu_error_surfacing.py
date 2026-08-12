"""Batch 159 热修：蓝湖证据发现 30s 超时兜底 + 空错误透出真实类型。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.services.external import lanhu_provider
from app.services.lanhu_evidence import page_discovery

URL = "https://lanhuapp.com/web/#/item/project/product?tid=t&pid=p&versionId=v&docId=d&docType=axure&pageId=pg"


class _FakeExtractor:
    def __init__(self, cookie: str = "") -> None:
        self.cookie = cookie
        self.calls = 0

    async def download_resources(self, url: str, output_dir: str, force_update: bool = False) -> dict:
        raise NotImplementedError

    async def get_pages_list(self, url: str) -> dict:
        return {
            "document_name": "测试文档",
            "pages": [{"id": "pg", "name": "首页", "folder": "", "filename": "home.html"}],
        }

    def parse_url(self, url: str) -> dict:
        return {"doc_id": "d", "project_id": "p", "version_id": "v", "page_id": "pg"}


def _install(monkeypatch, extractor) -> None:
    module = SimpleNamespace(COOKIE="", DDS_COOKIE="")

    class _ExtractorCls:
        def __init__(self, cookie: str = "") -> None:
            pass

    monkeypatch.setattr(lanhu_provider, "get_lanhu_cookie", lambda: "")
    monkeypatch.setattr(
        lanhu_provider,
        "_load_lanhu_runtime",
        lambda: SimpleNamespace(
            module=module,
            LanhuExtractor=_ExtractorCls,
            fix_html_files=lambda d: None,
            auth_error_types=(),
            login=None,
            save_cookie=None,
        ),
    )
    monkeypatch.setattr(lanhu_provider, "_create_lanhu_extractor", lambda runtime, cookie_override="": extractor)


def test_retries_once_on_timeout_then_succeeds(monkeypatch) -> None:
    calls = {"n": 0}

    class Ext(_FakeExtractor):
        async def download_resources(self, url: str, output_dir: str, force_update: bool = False) -> dict:
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ReadTimeout("read timed out")
            return {"status": "downloaded", "output_dir": output_dir}

    _install(monkeypatch, Ext())
    result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(URL))
    assert result["status"] == "success"
    assert calls["n"] == 2


def test_empty_str_exception_surfaces_type_name(monkeypatch) -> None:
    class Ext(_FakeExtractor):
        async def download_resources(self, url: str, output_dir: str, force_update: bool = False) -> dict:
            raise TimeoutError()  # str() 为空，旧逻辑会吞成「蓝湖页面发现失败」

    _install(monkeypatch, Ext())
    result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(URL))
    assert result["status"] == "failed"
    assert result["error"]  # 非空
    assert "TimeoutError" in result["error"]


def test_discover_pages_fallback_nonempty(monkeypatch) -> None:
    async def _fake(url: str, latest_version_only: bool = False, capture_all_pages: bool = True) -> dict:
        return {"status": "failed"}

    monkeypatch.setattr(
        lanhu_provider,
        "get_lanhu_pages_for_evidence",
        _fake,
    )
    with pytest.raises(ValueError) as ei:
        page_discovery.discover_pages(URL, capture_all_pages=True, latest_version_only=False)
    assert "蓝湖页面发现失败" in str(ei.value)
    assert "provider status=failed" in str(ei.value)


class _FakeResp:
    def __init__(self, text: str = "", payload: dict | None = None) -> None:
        self.text = text
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload or {}


class _FakeClient:
    def __init__(self, routes: dict[str, _FakeResp]) -> None:
        self.routes = routes

    async def get(self, url: str) -> _FakeResp:
        for key, resp in self.routes.items():
            if key in url:
                return resp
        return _FakeResp()


def test_scoped_download_only_target_folder(monkeypatch, tmp_path) -> None:
    """capture_all_pages=False 时只下载目标页及其同文件夹页面资源。"""
    from app.services.external import lanhu_provider as lp

    pages_info = {
        "document_name": "doc",
        "pages": [
            {"id": "pg", "name": "首页", "folder": "App", "filename": "home.html"},
            {"id": "pg2", "name": "同文件夹", "folder": "App", "filename": "other.html"},
            {"id": "pg3", "name": "其它文件夹", "folder": "Other", "filename": "skip.html"},
        ],
    }
    mapping = {
        "pages": {
            "home.html": {"html": {"sign_md5": "aaa"}, "mapping_md5": "bbb"},
            "other.html": {"html": {"sign_md5": "ccc"}, "mapping_md5": "ddd"},
            "skip.html": {"html": {"sign_md5": "eee"}, "mapping_md5": "fff"},
        }
    }
    client = _FakeClient({
        "http://x/map.json": _FakeResp(payload=mapping),
        "/aaa": _FakeResp(text="<html>home</html>"),
        "/bbb": _FakeResp(payload={"styles": {}, "scripts": {}, "images": {}}),
        "/ccc": _FakeResp(text="<html>other</html>"),
        "/ddd": _FakeResp(payload={"styles": {}, "scripts": {}, "images": {}}),
        "/eee": _FakeResp(text="<html>skip</html>"),
        "/fff": _FakeResp(payload={"styles": {}, "scripts": {}, "images": {}}),
    })

    class _Ext:
        client = None

        async def get_document_info(self, project_id, doc_id, team_id=None, page_id=None):
            return {"name": "doc", "versions": [{"id": "v9", "json_url": "http://x/map.json"}]}

        async def _download_page_resources(self, page_mapping, output_dir, skip_document_js=False):
            return None

        def _save_cache_meta(self, output_dir, meta_data):
            return None

    _Ext.client = client
    result = asyncio.run(lp._download_lanhu_resources_scoped(
        _Ext(), "http://x", str(tmp_path),
        {"project_id": "p", "doc_id": "d", "team_id": "t", "page_id": "pg"},
        pages_info,
        cdn_url="https://cdn",
        target_page_id="pg",
        capture_all_pages=False,
    ))
    assert result is not None
    assert result["status"] == "downloaded"
    assert result["reason"] == "scoped_pages"
    assert (tmp_path / "home.html").read_text(encoding="utf-8") == "<html>home</html>"
    assert (tmp_path / "other.html").exists()
    assert not (tmp_path / "skip.html").exists()


def test_scoped_download_falls_back_when_target_missing(tmp_path) -> None:
    from app.services.external import lanhu_provider as lp

    pages_info = {
        "pages": [{"id": "other", "name": "x", "folder": "A", "filename": "x.html"}],
    }

    class _Ext:
        client = _FakeClient({})

        async def get_document_info(self, project_id, doc_id, team_id=None, page_id=None):
            return {"versions": []}

    result = asyncio.run(lp._download_lanhu_resources_scoped(
        _Ext(), "http://x", str(tmp_path),
        {"project_id": "p", "doc_id": "d", "team_id": "t", "page_id": "missing"},
        pages_info,
        cdn_url="https://cdn",
        target_page_id="missing",
        capture_all_pages=False,
    ))
    assert result is None  # 目标页不在 sitemap → 回退全量下载



class TestBatch161LanhuAutoLogin:
    """Batch 161（G3）：蓝湖自动登录重试 + Cookie 持久化 + 错误区分。"""

    def test_login_retry_succeeds_on_second_attempt(self, monkeypatch) -> None:
        calls = {"n": 0}

        async def fake_login():
            calls["n"] += 1
            if calls["n"] == 1:
                return ""
            return "cookie-ok"

        async def no_sleep(_):
            return None

        monkeypatch.setenv("LANHU_USERNAME", "u")
        monkeypatch.setenv("LANHU_PASSWORD", "p")
        monkeypatch.setattr(lanhu_provider.asyncio, "sleep", no_sleep)

        runtime = SimpleNamespace(login=fake_login, save_cookie=None)
        cookie = asyncio.run(lanhu_provider._login_lanhu_with_retry(runtime))
        assert cookie == "cookie-ok"
        assert calls["n"] == 2

    def test_login_retry_all_fail_raises(self, monkeypatch) -> None:
        async def fake_login():
            return ""

        async def no_sleep(_):
            return None

        monkeypatch.setenv("LANHU_USERNAME", "u")
        monkeypatch.setenv("LANHU_PASSWORD", "p")
        monkeypatch.setattr(lanhu_provider.asyncio, "sleep", no_sleep)

        runtime = SimpleNamespace(login=fake_login, save_cookie=None)
        with pytest.raises(ValueError) as ei:
            asyncio.run(lanhu_provider._login_lanhu_with_retry(runtime))
        assert "2 次尝试" in str(ei.value)

    def test_login_retry_missing_credentials(self, monkeypatch) -> None:
        monkeypatch.delenv("LANHU_USERNAME", raising=False)
        monkeypatch.delenv("LANHU_PASSWORD", raising=False)

        async def fake_login():
            return "cookie"

        runtime = SimpleNamespace(login=fake_login, save_cookie=None)
        with pytest.raises(ValueError) as ei:
            asyncio.run(lanhu_provider._login_lanhu_with_retry(runtime))
        assert "未配置 LANHU_USERNAME/LANHU_PASSWORD" in str(ei.value)

    def test_persist_cookie_both_channels(self, monkeypatch) -> None:
        saved = []
        monkeypatch.setattr(lanhu_provider, "set_lanhu_cookie", lambda c: saved.append(("file", c)))
        runtime = SimpleNamespace(save_cookie=lambda c: saved.append(("runtime", c)))
        lanhu_provider._persist_lanhu_cookie("cookie-x", runtime)
        assert saved == [("file", "cookie-x"), ("runtime", "cookie-x")]
