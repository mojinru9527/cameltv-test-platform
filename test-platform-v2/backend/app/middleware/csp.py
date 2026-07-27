"""Content-Security-Policy middleware (P1-2/S2c).

Adds CSP header to all HTML responses as defense-in-depth against XSS.
Implemented as pure ASGI middleware for compatibility with BackgroundTasks.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


class CSPMiddleware:
    """ASGI middleware that appends Content-Security-Policy header to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.csp_enabled:
            await self.app(scope, receive, send)
            return

        async def _send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                # Avoid duplicates: remove any existing CSP header
                headers = [(k, v) for k, v in headers if k.lower() != b"content-security-policy"]
                headers.append(
                    (b"content-security-policy", settings.csp_header.encode("latin-1"))
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, _send)
