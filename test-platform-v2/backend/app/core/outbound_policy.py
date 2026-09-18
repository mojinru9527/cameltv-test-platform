"""Bounded outbound HTTP policy for URLs supplied by users.

This is intentionally smaller than a general HTTP client: it validates every
URL and redirect, rejects non-global IP addresses by default, and limits the
response body before any parser sees it.

Batch 258 / B1-1: the URL & IP policy itself now lives in `app.core.url_guard`.
This module keeps only the bounded-GET capability and reuses that single policy,
so there is exactly one implementation of "reject private / revalidate redirect".
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.core.url_guard import (
    UrlNotAllowedError,
    assert_public_url,
    resolve_addresses,  # noqa: F401  re-exported: existing callers/tests patch this name
)

# 保留历史名称：调用点与既有回归测试（tests/test_outbound_policy.py）零改动。
OutboundPolicyError = UrlNotAllowedError
"""Raised when a user-supplied outbound URL violates policy."""


@dataclass(frozen=True)
class SafeTextResponse:
    url: str
    status_code: int
    text: str


def validate_outbound_url(url: str, *, allow_private: bool = False) -> str:
    """Validate a single URL and return its normalized string."""
    return assert_public_url(url, allow_private=allow_private, resolver=resolve_addresses)


def safe_get_text(
    url: str,
    *,
    timeout: float | None = None,
    max_bytes: int | None = None,
    max_redirects: int | None = None,
    allow_private: bool = False,
) -> SafeTextResponse:
    """GET text with redirect revalidation and a hard response-size cap."""
    timeout = settings.outbound_request_timeout_seconds if timeout is None else timeout
    max_bytes = settings.outbound_max_response_bytes if max_bytes is None else max_bytes
    max_redirects = settings.outbound_max_redirects if max_redirects is None else max_redirects
    current = validate_outbound_url(url, allow_private=allow_private)

    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for _redirect in range(max_redirects + 1):
            with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise OutboundPolicyError("重定向响应缺少 Location")
                    if _redirect >= max_redirects:
                        raise OutboundPolicyError("重定向次数超过上限")
                    current = validate_outbound_url(
                        urljoin(current, location), allow_private=allow_private
                    )
                    continue

                response.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise OutboundPolicyError("目标响应体超过允许大小")
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                return SafeTextResponse(
                    url=current,
                    status_code=response.status_code,
                    text=b"".join(chunks).decode(encoding, errors="replace"),
                )
    raise OutboundPolicyError("重定向次数超过上限")
