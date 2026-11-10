"""M2 / TA-012：HTTP Driver 单测（MockTransport，无外网）。"""
from __future__ import annotations

import hashlib

import httpx

from app.aiqe.drivers.httpx_driver import HttpDriver, HttpRequestSpec


def make_driver(handler, *, max_body_bytes: int = 64 * 1024) -> HttpDriver:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    return HttpDriver(client, max_body_bytes=max_body_bytes)


def test_chain_success_records_evidence():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(201, json={"id": 2})

    driver = make_driver(handler)
    results = driver.execute_chain(
        [
            HttpRequestSpec("POST", "https://api.test/a", json_body={"x": 1}),
            HttpRequestSpec("GET", "https://api.test/b"),
        ]
    )
    assert [r.ok for r in results] == [True, True]
    assert results[0].request["method"] == "POST"
    assert results[0].request["json_body"] == {"x": 1}
    assert results[0].response["status_code"] == 200
    assert '"id"' in results[0].response["body"] and "1" in results[0].response["body"]
    assert results[1].status_code == 201


def test_chain_stops_at_first_failure_and_preserves_result():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/b":
            return httpx.Response(500, text="boom")
        return httpx.Response(200, text="ok")

    driver = make_driver(handler)
    results = driver.execute_chain(
        [
            HttpRequestSpec("GET", "https://api.test/a"),
            HttpRequestSpec("GET", "https://api.test/b"),
            HttpRequestSpec("GET", "https://api.test/c"),
        ]
    )
    assert calls == ["/a", "/b"]
    assert len(results) == 2
    assert results[0].ok is True
    assert results[1].ok is False and results[1].status_code == 500
    # 首次失败保留：不会因后续调用被覆盖
    assert results[0].response["body"] == "ok"


def test_sensitive_headers_redacted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    driver = make_driver(handler)
    result = driver.execute(
        HttpRequestSpec(
            "GET",
            "https://api.test/a",
            headers={"Authorization": "Bearer secret", "X-Api-Key": "k", "X-Trace": "t"},
        )
    )
    lowered = {k.lower(): v for k, v in result.request["headers"].items()}
    assert lowered["authorization"] == "***"
    assert lowered["x-api-key"] == "***"
    assert lowered["x-trace"] == "t"


def test_timeout_maps_to_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    driver = make_driver(handler)
    result = driver.execute(HttpRequestSpec("GET", "https://api.test/slow"))
    assert result.ok is False
    assert result.error == "TIMEOUT"
    assert result.status_code is None


def test_body_truncated():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="x" * 1000)

    driver = make_driver(handler, max_body_bytes=32)
    result = driver.execute(HttpRequestSpec("GET", "https://api.test/a"))
    assert result.response["body"].endswith("…[truncated]")
    assert len(result.response["body"].encode("utf-8")) < 200


def test_content_evidence_has_hash():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    driver = make_driver(handler)
    payload = b"raw-body"
    result = driver.execute(
        HttpRequestSpec("PUT", "https://api.test/a", content=payload)
    )
    assert result.request["content_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result.request["content_bytes"] == len(payload)
