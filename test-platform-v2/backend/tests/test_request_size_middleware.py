"""Regression tests for the streaming request-body cap."""
from __future__ import annotations

import asyncio
from typing import Any

from app.main import RequestSizeLimitMiddleware


def _run_request(body: bytes, *, content_length: str | None = None, max_bytes: int = 5) -> tuple[int, bytes]:
    sent: list[dict[str, Any]] = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def app(scope, receive, send):
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/upload",
        "headers": [(b"content-length", content_length.encode())] if content_length else [],
    }
    middleware = RequestSizeLimitMiddleware(app, max_bytes=max_bytes)
    asyncio.run(middleware(scope, receive, send))
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    response_body = next(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, response_body


def test_declared_content_length_is_rejected_early():
    status, _ = _run_request(b"", content_length="999")
    assert status == 413


def test_stream_without_content_length_is_counted():
    status, _ = _run_request(b"123456")
    assert status == 413


def test_small_stream_is_allowed():
    status, body = _run_request(b"1234")
    assert status == 200
    assert body == b"ok"
