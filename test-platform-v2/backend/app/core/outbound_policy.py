"""Bounded outbound HTTP policy for URLs supplied by users.

This is intentionally smaller than a general HTTP client: it validates every
URL and redirect, rejects non-global IP addresses by default, and limits the
response body before any parser sees it.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import settings


class OutboundPolicyError(ValueError):
    """Raised when a user-supplied outbound URL violates policy."""


@dataclass(frozen=True)
class SafeTextResponse:
    url: str
    status_code: int
    text: str


def resolve_addresses(host: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve all addresses and reject ambiguous/unavailable DNS results."""
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise OutboundPolicyError(f"无法解析目标主机: {host}") from exc
    addresses = set()
    for record in records:
        raw = record[4][0]
        try:
            addresses.add(ipaddress.ip_address(raw))
        except ValueError:
            continue
    if not addresses:
        raise OutboundPolicyError(f"目标主机没有可用地址: {host}")
    return addresses


def validate_outbound_url(url: str, *, allow_private: bool = False) -> str:
    """Validate a single URL and return its normalized string."""
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise OutboundPolicyError("仅允许 http/https URL")
    if not parsed.hostname:
        raise OutboundPolicyError("URL 缺少主机名")
    if parsed.username is not None or parsed.password is not None:
        raise OutboundPolicyError("URL 不允许携带用户名或密码")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise OutboundPolicyError("URL 端口无效") from exc
    if not 1 <= port <= 65535:
        raise OutboundPolicyError("URL 端口无效")

    if not allow_private:
        addresses = resolve_addresses(parsed.hostname, port)
        if any(not address.is_global for address in addresses):
            raise OutboundPolicyError("禁止访问私网、回环、链路本地或保留地址")
    return parsed.geturl()


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
