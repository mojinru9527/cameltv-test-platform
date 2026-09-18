"""Batch 258 / B1-2 — 凭据只发给白名单域名（关闭审计基线 S2）。

原实现用 `"pingcode" in host` 子串判定，`pingcode.attacker.tld` 会直接收割企业 Token。
改后：分类走配置化根域白名单（根域及其子域），非白名单主机回落 `generic`，
因此**结构上**不可能携带凭据 Header；并额外对显式传入的 `kind` 做一致性复核。
"""
from __future__ import annotations

import ipaddress

import httpx
import pytest

from app.core import url_guard
from app.services import requirement_source_service as rss
from app.services.requirement_source_service import RequirementSourceError, classify_url, fetch_url_content


@pytest.fixture
def settings_override(monkeypatch):
    def _override(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setattr(rss.settings, key, value)

    return _override


@pytest.fixture
def recorded_transport(monkeypatch):
    """安装 MockTransport 并返回记录到的请求列表。"""
    recorded: list[httpx.Request] = []

    def _install(response_factory):
        def _handle(request: httpx.Request) -> httpx.Response:
            recorded.append(request)
            return response_factory(request)

        mock = httpx.MockTransport(_handle)
        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=mock, **kwargs))
        return recorded

    monkeypatch.setattr(
        url_guard,
        "resolve_addresses",
        lambda host, port: {ipaddress.ip_address("93.184.216.34")},
    )
    return _install


class TestClassifyUrlWhitelist:
    """默认白名单内的厂商根域正常；伪装域名必须回落 generic。"""

    def test_vendor_domains_still_classify(self):
        assert classify_url("https://lanhuapp.com/x") == "lanhu"
        assert classify_url("https://x.pingcode.com/story/1") == "pingcode"
        assert classify_url("https://example.atlassian.net/wiki/spaces/A/pages/1") == "confluence"
        assert classify_url("https://example.com/req.html") == "generic"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://pingcode.attacker.tld/story/1", "generic"),
            ("https://atlassian.attacker.tld/wiki/x", "generic"),
            ("https://lanhuapp.attacker.tld/x", "generic"),
            ("https://notpingcode.com/x", "generic"),
            ("https://pingcode.com.attacker.tld/x", "generic"),
        ],
    )
    def test_lookalike_domains_are_not_trusted(self, url, expected):
        assert classify_url(url) == expected

    def test_case_insensitive_and_trailing_dot(self):
        assert classify_url("https://X.PingCode.com/story/1") == "pingcode"
        assert classify_url("https://x.pingcode.com./story/1") == "pingcode"

    def test_self_hosted_instance_via_config(self, settings_override):
        settings_override(requirement_pingcode_domains="pingcode.camel.internal,pingcode.com")
        assert classify_url("https://pingcode.camel.internal/story/9") == "pingcode"
        assert classify_url("https://sub.pingcode.camel.internal/story/9") == "pingcode"
        assert classify_url("https://x.pingcode.com/story/1") == "pingcode"
        assert classify_url("https://pingcode.evil.internal/story/9") == "generic"


class TestCredentialsNeverLeaveForUntrustedHosts:
    """核心安全断言：伪装域名收不到任何 Header。"""

    def test_lookalike_host_receives_no_authorization_header(
        self, settings_override, recorded_transport
    ):
        settings_override(pingcode_api_token="super-secret-token")
        requests = recorded_transport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"<html><head><title>evil</title></head><body>stolen?</body></html>",
            )
        )
        fetch_url_content("https://pingcode.attacker.tld/story/1")
        assert len(requests) == 1
        assert requests[0].headers.get("Authorization") is None

    def test_whitelisted_host_receives_authorization_header(
        self, settings_override, recorded_transport
    ):
        settings_override(pingcode_api_token="super-secret-token")
        requests = recorded_transport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"title": "需求", "description": "描述"},
            )
        )
        result = fetch_url_content("https://x.pingcode.com/story/1")
        assert result["kind"] == "pingcode"
        assert requests[0].headers.get("Authorization") == "Bearer super-secret-token"

    def test_explicit_kind_cannot_smuggle_credentials(
        self, settings_override, recorded_transport
    ):
        """调用方显式传 kind=pingcode 也不能把令牌发到非白名单域名。"""
        settings_override(pingcode_api_token="super-secret-token")
        requests = recorded_transport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html></html>")
        )
        with pytest.raises(RequirementSourceError) as exc:
            fetch_url_content("https://pingcode.attacker.tld/story/1", kind="pingcode")
        assert exc.value.kind == "guard"
        assert requests == []

    def test_confluence_token_also_restricted(self, settings_override, recorded_transport):
        settings_override(confluence_api_token="secret-confluence")
        requests = recorded_transport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"title": "t", "body": {"value": "v"}},
            )
        )
        fetch_url_content("https://example.atlassian.net/wiki/x")
        assert requests[0].headers.get("Authorization") == "Bearer secret-confluence"

        requests.clear()
        recorded = requests
        fetch_url_content("https://confluence.attacker.tld/wiki/x")
        assert recorded[-1].headers.get("Authorization") is None
