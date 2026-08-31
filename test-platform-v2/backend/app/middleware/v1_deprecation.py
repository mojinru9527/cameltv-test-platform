"""V1 API deprecation middleware (V40-008).

Adds RFC-style ``Deprecation`` / ``Sunset`` / ``Link`` response headers to v1
surfaces that are being retired, and best-effort records usage telemetry into
``legacy_usage_records``. The registry is intentionally data-driven and small by
default so operators can extend it; a header is only emitted for a known surface
so unknown v1 routes are untouched.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# surface path prefix -> successor/retirement metadata (V40-001/008).
# ``replacement_v2`` is the canonical v2 successor; ``sunset`` an ISO date.
V1_DEPRECATIONS: dict[str, dict[str, str]] = {
    "/api/v1/version-missions": {
        "replacement_v2": "/api/v2/missions",
        "sunset": "2027-01-01",
        "object_type": "VERSION_MISSION",
    },
    "/api/v1/test-plans": {
        "replacement_v2": "/api/v2/continuous/campaigns",
        "sunset": "2027-01-01",
        "object_type": "TEST_PLAN",
    },
    "/api/v1/datasets": {
        "replacement_v2": "/api/v2/data-sources",
        "sunset": "2027-01-01",
        "object_type": "DATASET",
    },
    "/api/v1/test-cases": {
        "replacement_v2": "/api/v2/scenarios",
        "sunset": "2027-01-01",
        "object_type": "TEST_CASE",
    },
    "/api/v1/schedules": {
        "replacement_v2": "/api/v2/continuous/triggers",
        "sunset": "2027-01-01",
        "object_type": "TEST_PLAN",
    },
}


def _deprecation_for(path: str) -> dict[str, str] | None:
    """Return the deprecation metadata for a v1 path, matching longest-prefix."""
    best: tuple[int, dict[str, str]] | None = None
    for prefix, meta in V1_DEPRECATIONS.items():
        if path.startswith(prefix):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), {**meta, "prefix": prefix})
    return None if best is None else best[1]


def deprecation_headers_for(path: str) -> list[tuple[str, str]]:
    """Return RFC deprecation headers for a v1 path (empty when not deprecated)."""
    meta = _deprecation_for(path)
    if meta is None:
        return []
    replacement = meta["replacement_v2"]
    sunset = meta.get("sunset", "")
    headers: list[tuple[str, str]] = [("Deprecation", "true")]
    if sunset:
        headers.append(("Sunset", sunset))
    if replacement:
        headers.append(("Link", f'<{replacement}>; rel="successor-version"'))
    return headers


def record_deprecation_usage(path: str, method: str) -> None:
    """Best-effort telemetry write; never raises (observability only)."""
    meta = _deprecation_for(path)
    if meta is None:
        return
    try:
        from app.core.db import SessionLocal
        from app.modules.aitde.legacy_cutover.service import LegacyUsageInventoryService

        db = SessionLocal()
        try:
            LegacyUsageInventoryService.record(
                db,
                0,
                {
                    "consumer_type": "EXTERNAL",
                    "surface_kind": "ENDPOINT",
                    "path": path,
                    "method": method,
                    "object_type": meta["object_type"],
                    "replacement_v2": meta["replacement_v2"],
                    "deprecation_stage": "DEPRECATED",
                },
            )
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - telemetry must never gate a request
        pass


class V1DeprecationMiddleware:
    """ASGI middleware injecting deprecation headers on matched v1 routes."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = (scope.get("method") or "GET").upper()
        headers = deprecation_headers_for(path)
        if not headers:
            await self.app(scope, receive, send)
            return

        # Fire-and-forget telemetry (no DB session in this context).
        try:
            import asyncio
            from functools import partial

            asyncio.get_running_loop().run_in_executor(
                None, partial(record_deprecation_usage, path, method)
            )
        except Exception:  # noqa: BLE001
            pass

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() not in {
                        b"deprecation", b"sunset", b"link"
                    }
                ]
                message = {
                    **message,
                    "headers": existing
                    + [(k.lower().encode(), v.encode()) for k, v in headers],
                }
            await send(message)

        await self.app(scope, receive, _send)
