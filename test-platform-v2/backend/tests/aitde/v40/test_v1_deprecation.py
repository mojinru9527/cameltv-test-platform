"""AITDE V4.0 (V40-008) v1 API deprecation policy tests."""

from __future__ import annotations

import pytest

from app.middleware.v1_deprecation import (
    V1_DEPRECATIONS,
    V1DeprecationMiddleware,
    _deprecation_for,
    deprecation_headers_for,
)


def test_deprecation_headers_for_known_surface():
    headers = dict(deprecation_headers_for("/api/v1/test-plans"))
    replacement = V1_DEPRECATIONS["/api/v1/test-plans"]["replacement_v2"]
    assert headers["Deprecation"] == "true"
    assert headers["Sunset"] == "2027-01-01"
    assert headers["Link"] == f'<{replacement}>; rel="successor-version"'


def test_deprecation_headers_for_unknown_surface():
    assert deprecation_headers_for("/api/v1/anything-not-registered") == []
    assert deprecation_headers_for("/api/v2/missions") == []
    assert deprecation_headers_for("/health") == []


def test_longest_prefix_match():
    meta = _deprecation_for("/api/v1/version-missions/123")
    assert meta is not None
    # A more specific prefix wins when present.
    assert _deprecation_for("/api/v1/test-plans/9/cases")["prefix"] == "/api/v1/test-plans"


@pytest.mark.anyio
async def test_middleware_injects_headers_on_matched_path():
    captured = {}

    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def send(message):
        captured.setdefault("messages", []).append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/datasets",
        "headers": [],
        "query_string": b"",
        "server": ("x", 80),
        "client": ("x", 1),
        "scheme": "http",
        "http_version": "1.1",
    }
    mw = V1DeprecationMiddleware(mock_app)
    await mw(scope, receive, send)

    start = captured["messages"][0]
    headers = {k.decode().lower(): v.decode() for k, v in start["headers"]}
    assert headers["deprecation"] == "true"
    assert headers["sunset"] == "2027-01-01"
    assert "successor-version" in headers["link"]


@pytest.mark.anyio
async def test_middleware_leaves_unknown_path_untouched():
    captured = {}

    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": [(b"x-custom", b"1")]})
        await send({"type": "http.response.body", "body": b"ok"})

    async def send(message):
        captured.setdefault("messages", []).append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "query_string": b"",
        "server": ("x", 80),
        "client": ("x", 1),
        "scheme": "http",
        "http_version": "1.1",
    }
    mw = V1DeprecationMiddleware(mock_app)
    await mw(scope, receive, send)

    start = captured["messages"][0]
    headers = {k.decode().lower(): v.decode() for k, v in start["headers"]}
    assert "deprecation" not in headers
    assert headers["x-custom"] == "1"
