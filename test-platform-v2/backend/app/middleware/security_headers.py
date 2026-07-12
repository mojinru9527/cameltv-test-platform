"""Security headers middleware (C3).

Adds standard OWASP-recommended security response headers to every HTTP
response. Implemented as pure ASGI middleware to avoid BackgroundTasks
issues with BaseHTTPMiddleware.

Headers added:
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  X-XSS-Protection: 0
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that injects security headers into every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not settings.security_headers_enabled:
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"x-xss-protection"] = b"0"
                headers[b"permissions-policy"] = (
                    b"camera=(), microphone=(), geolocation=()"
                )
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_with_headers)
