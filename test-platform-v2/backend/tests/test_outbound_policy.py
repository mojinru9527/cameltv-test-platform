"""Regression tests for bounded outbound URL policy."""
from __future__ import annotations

import pytest

from app.core import outbound_policy


def test_private_and_loopback_targets_are_rejected(monkeypatch):
    monkeypatch.setattr(
        outbound_policy,
        "resolve_addresses",
        lambda host, port: {__import__("ipaddress").ip_address("127.0.0.1")},
    )
    with pytest.raises(outbound_policy.OutboundPolicyError, match="私网"):
        outbound_policy.validate_outbound_url("http://internal.example/openapi.json")


def test_public_target_is_allowed(monkeypatch):
    import ipaddress

    monkeypatch.setattr(
        outbound_policy,
        "resolve_addresses",
        lambda host, port: {ipaddress.ip_address("93.184.216.34")},
    )
    assert (
        outbound_policy.validate_outbound_url("https://example.com/openapi.json")
        == "https://example.com/openapi.json"
    )


def test_response_size_cap_is_enforced(monkeypatch):
    class FakeResponse:
        is_redirect = False
        status_code = 200
        headers = {}
        encoding = "utf-8"

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"1234"
            yield b"5678"

    class FakeStream:
        def __enter__(self):
            return FakeResponse()

        def __exit__(self, *args):
            return False

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return FakeStream()

    monkeypatch.setattr(outbound_policy, "resolve_addresses", lambda host, port: {__import__("ipaddress").ip_address("93.184.216.34")})
    monkeypatch.setattr(outbound_policy.httpx, "Client", FakeClient)

    with pytest.raises(outbound_policy.OutboundPolicyError, match="响应体"):
        outbound_policy.safe_get_text("https://example.com/spec.json", max_bytes=5)
