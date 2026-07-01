"""CSRF protection middleware (P1-1/S1d, refined in P1-C1).

Validates Origin / Referer headers for state-changing requests to prevent
cross-site request forgery when httpOnly cookies carry the auth token.

Bypass logic: only /api/v1/open is excluded (API Token Bearer tpat_xxx — no cookie).
All other endpoints including /api/v1/tokens/* are CSRF-protected (JWT Cookie auth).

Deliberately implemented as pure ASGI middleware to avoid issues with
BaseHTTPMiddleware and BackgroundTasks.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings

logger = logging.getLogger("csrf")

# Safe methods that do not require CSRF validation
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Path prefixes that bypass CSRF.
# Only /api/v1/open uses API Token (Bearer tpat_xxx) — no cookie, no CSRF needed.
# /api/v1/tokens management endpoints use JWT cookie auth and are now CSRF-protected.
_BYPASS_PREFIXES = ("/api/v1/open",)


class CSRFMiddleware:
    """ASGI middleware that checks Origin/Referer for state-changing requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not settings.csrf_enabled:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        if method in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(_BYPASS_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Collect request headers (ASGI scope headers are iterable of (key, value) bytes)
        headers: dict[str, str] = {}
        for raw_key, raw_val in scope.get("headers", []):
            headers[raw_key.decode("latin-1").lower()] = raw_val.decode("latin-1")

        origin = headers.get("origin", "")
        referer = headers.get("referer", "")

        allowed = self._allowed_origins()
        if not self._is_origin_allowed(origin, referer, allowed):
            logger.warning(
                "CSRF check failed — Origin=%s Referer=%s Path=%s",
                origin or "<missing>",
                referer or "<missing>",
                path,
            )
            await self._forbidden(send)
            return

        await self.app(scope, receive, send)

    def _allowed_origins(self) -> list[str]:
        """Return the list of allowed origin patterns."""
        if settings.csrf_allowed_origins:
            return [o.strip() for o in settings.csrf_allowed_origins.split(",") if o.strip()]
        return settings.cors_origins

    def _is_origin_allowed(self, origin: str, referer: str, allowed: list[str]) -> bool:
        """Check whether Origin or Referer matches one of the allowed origins."""
        check_val = origin or referer
        if not check_val:
            # No Origin and no Referer — could be same-origin request from
            # a privacy-focused browser; allow it (SameSite cookies add
            # a second layer of protection).
            return True

        try:
            parsed = urlparse(check_val)
            check_host = parsed.netloc or parsed.path.split("/")[0] if parsed.path else ""
        except Exception:
            return False

        for a in allowed:
            if a == "*":
                return True
            try:
                allowed_host = urlparse(a).netloc or a
            except Exception:
                allowed_host = a
            if check_host == allowed_host:
                return True
            # Also allow subdomains
            if check_host.endswith("." + allowed_host):
                return True

        return False

    async def _forbidden(self, send: Send) -> None:
        body = b'{"code":403,"message":"CSRF check failed","data":null}'
        await send({
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
