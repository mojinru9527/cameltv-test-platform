"""v1.4 FIX-003：HTTP Driver 安全与业务化测试。"""
from __future__ import annotations

import httpx
import pytest

from app.aiqe.drivers.httpx_driver import (
    HttpDriver,
    HttpRequestSpec,
    UnsafeTargetError,
    retry_allowed,
    validate_target,
)


def test_ssrf_blocks_localhost_private_and_metadata():
    for url in (
        "http://localhost:8000/x",
        "http://127.0.0.1/x",
        "http://10.0.0.1/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/x",
        "file:///etc/passwd",
        "https://user:pass@api.test/x",
    ):
        with pytest.raises(UnsafeTargetError):
            validate_target(url)


def test_allowlist_exact_and_wildcard():
    assert validate_target(
        "https://api.example.com/x", allowed_hosts=["api.example.com"]
    )
    assert validate_target(
        "https://a.example.com/x", allowed_hosts=["*.example.com"]
    )
    with pytest.raises(UnsafeTargetError):
        validate_target("https://evil.com/x", allowed_hosts=["*.example.com"])


def test_private_allowed_only_when_explicitly_enabled():
    assert validate_target("http://127.0.0.1:8000/x", allow_private=True)
    with pytest.raises(UnsafeTargetError):
        validate_target("http://127.0.0.1:8000/x", allow_private=False)


def test_retry_policy_rejects_non_idempotent_write():
    assert retry_allowed("GET") is True
    assert retry_allowed("PUT") is True
    assert retry_allowed("POST") is False
    assert retry_allowed("POST", idempotency_key="order-1") is True
    assert retry_allowed("DELETE", policy="never") is False


def test_unsafe_target_is_evidence_failure_not_pass():
    driver = HttpDriver(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    result = driver.execute(HttpRequestSpec("GET", "http://127.0.0.1:9/x"))
    assert result.ok is False
    assert result.error_class == "SSRF_BLOCKED"
    assert result.status_code is None


def test_correlation_id_and_json_data():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-AIQE-Correlation-ID"] == "corr-1"
        return httpx.Response(200, json={"code": 0})

    driver = HttpDriver(
        httpx.Client(transport=httpx.MockTransport(handler)),
        enforce_ssrf=False,
    )
    result = driver.execute(
        HttpRequestSpec("GET", "https://api.test/x", correlation_id="corr-1")
    )
    assert result.data["json"] == {"code": 0}
    assert result.data["status_code"] == 200
    assert result.request["correlation_id"] == "corr-1"


def test_execution_json_preserved_but_evidence_redacted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"token": "tok-1", "ok": True})

    driver = HttpDriver(
        httpx.Client(transport=httpx.MockTransport(handler)),
        enforce_ssrf=False,
    )
    result = driver.execute(HttpRequestSpec("POST", "https://api.test/login"))
    # 执行/变量提取需要真实 token；证据正文必须脱敏。
    assert result.data["json"]["token"] == "tok-1"
    assert "tok-1" not in result.response["body"]
    assert "***" in result.response["body"]


def test_query_values_redacted_in_evidence():
    driver = HttpDriver(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200))),
        enforce_ssrf=False,
    )
    result = driver.execute(
        HttpRequestSpec("GET", "https://api.test/x?token=abc&page=1")
    )
    assert "token=***" in result.request["url"]
    assert "abc" not in result.request["url"]
