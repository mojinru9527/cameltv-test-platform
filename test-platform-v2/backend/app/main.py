"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.api.v2.router import router as v2_router
from app.core.config import settings
from app.core.db import Base, engine
from app.core.exceptions import APIException, api_exception_handler

logger = logging.getLogger(__name__)

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
        logger.warning("[security] WARNING — configuration issues detected:")
        for issue in security_issues:
            logger.warning("  - %s", issue)
        if settings.environment == "production":
            raise SystemExit(
                "\n[security] FATAL — refusing to start in production with insecure configuration.\n"
                + "  Set SECRET_KEY, ADMIN_PASSWORD, TESTER_PASSWORD, and AI_API_KEY "
                + "via environment or .env file.\n"
            )

    # ── 蓝湖证据存储落点（Batch 140/141）：确保目录存在并打印，便于确认持久卷挂载 ──
    try:
        from app.api.v1.lanhu_evidence_jobs import _storage_base

        storage_base = _storage_base()
        storage_base.mkdir(parents=True, exist_ok=True)
        # Batch 141: Railway 卷默认以 root 挂载；把目录权限放宽到 755，
        # 避免后续降权/非 root 进程读取或写入证据文件时再次 Permission denied。
        try:
            storage_base.chmod(0o755)
        except OSError:
            pass
        logger.info(
            "[storage] Lanhu evidence storage base: %s （生产请用持久卷挂载，否则 Railway 重建会清空截图）",
            storage_base,
        )
    except PermissionError as exc:
        logger.warning(
            "[storage] Lanhu evidence storage init failed: %s — "
            "Railway 卷以 root 挂载而容器以非 root 运行。请在 Railway 后端服务 Variables 设置 "
            "RAILWAY_RUN_UID=0 并重新部署；或先以 root 执行 chown -R 10001:10001 /app/storage。",
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[storage] Lanhu evidence storage init failed: %s", exc)

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    from app.seed import run_seed

    run_seed()

    from app.core.scheduler import init_scheduler, shutdown_scheduler

    init_scheduler()

    # ── V2.6: Auto-sync scheduler for external integrations ──
    if settings.sync_enabled:
        from app.core.db import SessionLocal
        from app.models.integration import IntegrationConfig

        _sync_db = SessionLocal()
        try:
            _configs = _sync_db.query(IntegrationConfig).filter(
                IntegrationConfig.enabled,
                IntegrationConfig.sync_interval_minutes > 0,
            ).all()
            for _cfg in _configs:
                from app.services.sync.engine import run_scheduled_sync
                from apscheduler.triggers.interval import IntervalTrigger
                from app.core.scheduler import scheduler as _scheduler

                job_id = f"sync_integration_{_cfg.id}"
                if not _scheduler.get_job(job_id):
                    _scheduler.add_job(
                        run_scheduled_sync,
                        trigger=IntervalTrigger(minutes=_cfg.sync_interval_minutes),
                        args=[_cfg.id],
                        id=job_id,
                        name=f"Sync integration #{_cfg.id} ({_cfg.provider_type})",
                        replace_existing=True,
                    )
                    logger.info("[sync] Registered auto-sync job for integration #%s (%s) every %smin", _cfg.id, _cfg.name, _cfg.sync_interval_minutes)
        except Exception as exc:
            logger.warning("[sync] WARNING — failed to register auto-sync jobs: %s", exc)
        finally:
            _sync_db.close()

    from app.services.ai_tasks import ensure_worker_running as ensure_ai_worker

    ensure_ai_worker()

    try:
        yield
    finally:
        from app.services.ai_tasks import shutdown_worker as shutdown_ai_worker
        from app.services.api_task_worker import (
            shutdown_processor as shutdown_api_task_worker,
        )
        from app.services.knowledge.agent_queue import (
            shutdown_processor as shutdown_agent_queue,
        )

        shutdown_api_task_worker()
        shutdown_ai_worker()
        shutdown_agent_queue()
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

# C3: Security response headers (X-Content-Type-Options, X-Frame-Options, etc.)
from app.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402

app.add_middleware(SecurityHeadersMiddleware)

# P1-2/S2c: Content-Security-Policy header (defense-in-depth against XSS)
from app.middleware.csp import CSPMiddleware  # noqa: E402

app.add_middleware(CSPMiddleware)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(api_router)
app.include_router(v2_router)


@app.get("/health", tags=["system"], summary="Health check")
def health():
    return {"status": "ok", "version": settings.app_version}
