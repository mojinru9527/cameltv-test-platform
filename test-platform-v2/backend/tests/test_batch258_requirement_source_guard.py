"""Batch 258 / B1-1 — 需求抓取与发布包导入接入统一出网守卫。

DoD（backlog B1-1）：5 个恶意 URL 全部被拒 —— `127.0.0.1` / `169.254.169.254` /
内网域名 / 重定向跳转 / 大响应。两个调用点（需求导入 `requirement_docs.py`、
发布包导入 `release_bundles_core.py`）都经 `fetch_url_content()`，故本文件覆盖两处。

传输层用 `httpx.MockTransport` 注入真实 httpx 客户端，不替换 Response/Headers，
避免替身与真实语义漂移。
"""
from __future__ import annotations

import ipaddress

import httpx
import pytest

from app.core import url_guard
from app.services import requirement_source_service as rss
from app.services.requirement_source_service import RequirementSourceError, fetch_url_content

PUBLIC_IP = "93.184.216.34"


def use_public_dns(monkeypatch) -> None:
    """注入解析结果：域名 → 公网地址；字面量 IP → 保持原值。

    刻意不写成 `lambda host, port: {PUBLIC_IP}`：那会把 `127.0.0.1` 也伪装成公网地址，
    让「字面量内网 IP 必须被拒」这条断言失去意义（守卫生效却测不出来）。
    """

    def _resolve(host: str, port: int):
        try:
            return {ipaddress.ip_address(host)}
        except ValueError:
            return {ipaddress.ip_address(PUBLIC_IP)}

    monkeypatch.setattr(url_guard, "resolve_addresses", _resolve)


class Transport:
    """记录每一跳访问过的 URL / 请求头，并按 handler 返回响应。"""

    def __init__(self, handler):
        self._handler = handler
        self.visited: list[str] = []
        self.requests: list[httpx.Request] = []

    def install(self, monkeypatch) -> "Transport":
        def _handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            self.visited.append(str(request.url))
            return self._handler(request, self)

        mock = httpx.MockTransport(_handle)
        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=mock, **kwargs))
        return self

    def header(self, index: int, name: str) -> str | None:
        return self.requests[index].headers.get(name)


@pytest.fixture
def settings_override(monkeypatch):
    """临时改写运行期 settings 字段（pytest 结束时自动还原）。"""

    def _override(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setattr(rss.settings, key, value)

    return _override


def _forbid_network(request, recorder):
    raise AssertionError(f"守卫应在出网前拒绝，却发起了请求: {request.url}")


class TestMaliciousUrlsRejected:
    """5 类恶意 URL：4 类在出网前拒绝，1 类在流式读取阶段拒绝。"""

    def test_loopback_is_rejected_without_any_request(self, monkeypatch):
        use_public_dns(monkeypatch)
        transport = Transport(_forbid_network).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("http://127.0.0.1/req")
        assert exc.value.kind == "guard"
        assert transport.visited == []

    def test_link_local_metadata_endpoint_is_rejected(self, monkeypatch):
        use_public_dns(monkeypatch)
        transport = Transport(_forbid_network).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("http://169.254.169.254/latest/meta-data/")
        assert exc.value.kind == "guard"
        assert transport.visited == []

    def test_internal_hostname_is_rejected(self, monkeypatch):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("10.0.0.5")}
        )
        transport = Transport(_forbid_network).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("http://internal.camel.local/req")
        assert exc.value.kind == "guard"
        assert transport.visited == []

    def test_redirect_hijack_to_metadata_is_rejected(self, monkeypatch):
        use_public_dns(monkeypatch)
        transport = Transport(
            lambda request, recorder: httpx.Response(
                302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
            )
        ).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("https://example.com/req")
        assert exc.value.kind == "guard"
        # 只允许访问首跳目标；重定向目标必须在出网前被拦下
        assert transport.visited == ["https://example.com/req"]

    def test_oversized_response_is_rejected(self, monkeypatch, settings_override):
        settings_override(outbound_max_response_bytes=32)
        use_public_dns(monkeypatch)
        Transport(
            lambda request, recorder: httpx.Response(
                200, headers={"content-type": "text/html"}, content=b"<html>" + b"x" * 4096
            )
        ).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("https://example.com/big.html")
        assert exc.value.kind == "guard"
        assert "大小" in str(exc.value)

    def test_excessive_redirects_are_rejected(self, monkeypatch, settings_override):
        settings_override(outbound_max_redirects=2)
        use_public_dns(monkeypatch)
        transport = Transport(
            lambda request, recorder: httpx.Response(
                302, headers={"location": "https://example.com/next"}
            )
        ).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("https://example.com/req")
        assert exc.value.kind == "guard"
        assert len(transport.visited) <= 3

    def test_redirect_without_location_is_rejected(self, monkeypatch):
        use_public_dns(monkeypatch)
        Transport(lambda request, recorder: httpx.Response(302)).install(monkeypatch)
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("https://example.com/req")
        assert exc.value.kind == "guard"


class TestHappyPathStillWorks:
    """守卫不得破坏既有正常链路（含鉴权 Header 透传）。"""

    def test_public_html_target_is_fetched(self, monkeypatch):
        use_public_dns(monkeypatch)
        Transport(
            lambda request, recorder: httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content="<html><head><title>需求标题</title></head><body><p>正文</p></body></html>".encode(),
            )
        ).install(monkeypatch)
        result = fetch_url_content("https://example.com/req.html")
        assert result["kind"] == "generic"
        assert "正文" in result["content"]
        assert result["title"] == "需求标题"

    def test_public_redirect_chain_is_followed(self, monkeypatch):
        use_public_dns(monkeypatch)

        def handler(request, recorder):
            if str(request.url) == "https://example.com/req":
                return httpx.Response(302, headers={"location": "/real"})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"<html><head><title>T</title></head><body>ok</body></html>",
            )

        transport = Transport(handler).install(monkeypatch)
        assert "ok" in fetch_url_content("https://example.com/req")["content"]
        assert transport.visited == ["https://example.com/req", "https://example.com/real"]

    def test_headers_reach_the_transport(self, monkeypatch):
        use_public_dns(monkeypatch)
        transport = Transport(
            lambda request, recorder: httpx.Response(
                200, headers={"content-type": "application/json"}, json={"title": "t", "description": "d"}
            )
        ).install(monkeypatch)
        rss._request("https://example.com/api", headers={"Authorization": "Bearer t"})
        assert transport.header(0, "Authorization") == "Bearer t"
