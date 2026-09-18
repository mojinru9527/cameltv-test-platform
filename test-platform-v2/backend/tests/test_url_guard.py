"""Batch 258 / B1-1 — 统一出网守卫单测（私网/回环/链路本地/重定向/凭据）。

本文件是 backlog B1-1 DoD 的 5 个恶意 URL 回归入口之一（纯 URL 层）。
响应体上限与重定向跳转的端到端回归见 tests/test_batch258_requirement_source_guard.py。
"""
from __future__ import annotations

import ipaddress

import pytest

from app.core import outbound_policy, url_guard


class TestAssertPublicUrl:
    """assert_public_url 必须逐类拒绝并给出可读原因。"""

    def test_rejects_loopback_literal(self):
        with pytest.raises(url_guard.UrlNotAllowedError) as exc:
            url_guard.assert_public_url("http://127.0.0.1/admin")
        assert "私网" in str(exc.value)

    def test_rejects_link_local_metadata_endpoint(self):
        with pytest.raises(url_guard.UrlNotAllowedError) as exc:
            url_guard.assert_public_url("http://169.254.169.254/latest/meta-data/")
        assert "私网" in str(exc.value)

    def test_rejects_private_hostname(self, monkeypatch):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("10.0.0.5")}
        )
        with pytest.raises(url_guard.UrlNotAllowedError):
            url_guard.assert_public_url("http://internal.camel.local/req")

    def test_rejects_any_private_address_when_multiple_records(self, monkeypatch):
        """DNS 返回多个地址时，只要有一个非公网地址就必须拒绝（防解析抖动绕过）。"""
        monkeypatch.setattr(
            url_guard,
            "resolve_addresses",
            lambda host, port: {
                ipaddress.ip_address("93.184.216.34"),
                ipaddress.ip_address("192.168.1.10"),
            },
        )
        with pytest.raises(url_guard.UrlNotAllowedError):
            url_guard.assert_public_url("https://mixed.example/req")

    def test_allows_public_host(self, monkeypatch):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("93.184.216.34")}
        )
        assert url_guard.assert_public_url("https://example.com/req") == "https://example.com/req"

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/x",
            "file:///etc/passwd",
            "https://user:pass@example.com/x",
            "http:///no-host",
        ],
    )
    def test_rejects_non_http_or_credentialed_or_hostless(self, monkeypatch, url):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("93.184.216.34")}
        )
        with pytest.raises(url_guard.UrlNotAllowedError):
            url_guard.assert_public_url(url)

    def test_unresolvable_host_is_rejected(self, monkeypatch):
        def _boom(host, port):
            raise url_guard.UrlNotAllowedError(f"无法解析目标主机: {host}")

        monkeypatch.setattr(url_guard, "resolve_addresses", _boom)
        with pytest.raises(url_guard.UrlNotAllowedError, match="无法解析"):
            url_guard.assert_public_url("https://does-not-exist.invalid/req")


class TestRedirectRevalidation:
    """重定向后的最终地址必须二次校验（B1-1 DoD 第 4 类）。"""

    def test_redirect_to_loopback_is_rejected(self):
        # 故意不注入解析器：字面量 IP 无需 DNS 即可解析，注入会把 127.0.0.1 伪装成公网地址。
        with pytest.raises(url_guard.UrlNotAllowedError):
            url_guard.assert_public_url_after_redirect("https://example.com/req", "http://127.0.0.1/evil")

    def test_relative_redirect_is_resolved_then_checked(self, monkeypatch):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("93.184.216.34")}
        )
        assert (
            url_guard.assert_public_url_after_redirect("https://example.com/a/req", "../b/req")
            == "https://example.com/b/req"
        )

    def test_absolute_redirect_to_public_host_is_allowed(self, monkeypatch):
        monkeypatch.setattr(
            url_guard, "resolve_addresses", lambda host, port: {ipaddress.ip_address("93.184.216.34")}
        )
        assert (
            url_guard.assert_public_url_after_redirect("https://example.com/req", "https://cdn.example.org/x")
            == "https://cdn.example.org/x"
        )


class TestOutboundPolicyDelegates:
    """收敛验证：outbound_policy 复用同一份策略，不保留第二套 IP 判定。"""

    def test_outbound_policy_uses_url_guard_primitives(self):
        assert outbound_policy.OutboundPolicyError is url_guard.UrlNotAllowedError

    def test_outbound_policy_still_rejects_private(self, monkeypatch):
        monkeypatch.setattr(
            outbound_policy, "resolve_addresses", lambda host, port: {ipaddress.ip_address("127.0.0.1")}
        )
        with pytest.raises(outbound_policy.OutboundPolicyError, match="私网"):
            outbound_policy.validate_outbound_url("http://internal.example/openapi.json")

    def test_outbound_policy_allows_public(self, monkeypatch):
        monkeypatch.setattr(
            outbound_policy, "resolve_addresses", lambda host, port: {ipaddress.ip_address("93.184.216.34")}
        )
        assert (
            outbound_policy.validate_outbound_url("https://example.com/openapi.json")
            == "https://example.com/openapi.json"
        )

    def test_outbound_policy_allow_private_flag_still_honoured(self, monkeypatch):
        monkeypatch.setattr(
            outbound_policy, "resolve_addresses", lambda host, port: {ipaddress.ip_address("10.1.2.3")}
        )
        assert (
            outbound_policy.validate_outbound_url("http://10.1.2.3/spec.json", allow_private=True)
            == "http://10.1.2.3/spec.json"
        )
