"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import Base, engine
from app.core.exceptions import APIException, api_exception_handler


@asynccontextmanager
async def lifespan(_: FastAPI):
    import app.models  # noqa: F401

    # ── security validation (fail early in production) ──
    security_issues = settings.validate_security()
    if security_issues:
        print("[security] WARNING — configuration issues detected:")
        for issue in security_issues:
            print(f"  • {issue}")
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

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(api_router)


@app.get("/health", tags=["system"], summary="Health check")
def health():
    return {"status": "ok", "version": settings.app_version}
