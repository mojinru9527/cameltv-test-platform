"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import Base, engine
from app.core.exceptions import APIException, api_exception_handler

# P1-S6c: 全局请求体大小限制 (100 MB)
_MAX_BODY_BYTES = 100 * 1024 * 1024


class RequestSizeLimitMiddleware:
    """ASGI middleware that rejects requests with Content-Length > 100 MB."""

    def __init__(self, app: ASGIApp, max_bytes: int = _MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers: dict[bytes, bytes] = {}
            for k, v in scope.get("headers", []):
                headers[k] = v
            content_length = headers.get(b"content-length")
            if content_length:
                try:
                    cl = int(content_length.decode())
                except (ValueError, UnicodeDecodeError):
                    cl = 0
                if cl > self.max_bytes:
                    body = (
                        b'{"code":413,"message":"'
                        b'Request body exceeds 100 MB limit",'
                        b'"data":null}'
                    )
                    await send({
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    })
                    await send({"type": "http.response.body", "body": body})
                    return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI):
    import app.models  # noqa: F401

    # ── security validation (fail early in production) ──
    security_issues = settings.validate_security()
    if security_issues:
        print("[security] WARNING — configuration issues detected:")
        for issue in security_issues:
            print(f"  - {issue}")
        if settings.environment == "production":
            raise SystemExit(
                "\n[security] FATAL — refusing to start in production with insecure configuration.\n"
                + "  Set SECRET_KEY, ADMIN_PASSWORD, and AI_API_KEY via environment or .env file.\n"
            )

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    from app.seed import run_seed

    run_seed()

    from app.core.scheduler import init_scheduler, shutdown_scheduler

    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CamelTv test platform REST API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# P1-1/S1d: CSRF protection (validate Origin/Referer for state-changing requests)
from app.middleware.csrf import CSRFMiddleware  # noqa: E402

app.add_middleware(CSRFMiddleware)

# P1-S6c: Global request body size limit (100 MB)
app.add_middleware(RequestSizeLimitMiddleware)

# P1-2/S2c: Content-Security-Policy header (defense-in-depth against XSS)
from app.middleware.csp import CSPMiddleware  # noqa: E402

app.add_middleware(CSPMiddleware)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(api_router)


@app.get("/health", tags=["system"], summary="Health check")
def health():
    return {"status": "ok", "version": settings.app_version}
