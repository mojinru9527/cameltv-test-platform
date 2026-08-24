"""Standalone release-control console — independent of the test platform.

This service is the ONLY deployment control plane for the Tencent Cloud
production test-platform. It intentionally has no dependency on the
test-platform backend app (no SQLAlchemy ORM, no business models): it reads
and writes the executor-owned release-control SQLite store directly and runs
the SSH executor to deploy/rollback/backup the target host.

It lives OUTSIDE the target system so that a broken test platform can still
be published or rolled back through this console.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tencent_executor import (
    ExecutorCommandFailed,
    ExecutorNotConfigured,
    build_executor_from_settings,
)

app = FastAPI(title="CamelTv Release Console", version="1.0")

# Allow the standalone console origins (same-host subdomain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://release.swiftbugs.cn", "http://localhost:8003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── runtime settings (env-based, fail-closed) ─────────────────────────────


class ConsoleSettings:
    """Minimal env-backed settings mirroring the platform config keys."""

    def __init__(self) -> None:
        import os

        def _env(key: str, default: str = "") -> str:
            return os.environ.get(key, default)

        self.release_control_database_path = _env("RELEASE_CONTROL_DATABASE_PATH")
        self.tencent_executor_host = _env("TENCENT_EXECUTOR_HOST")
        self.tencent_executor_user = _env("TENCENT_EXECUTOR_USER")
        self.tencent_executor_ssh_key = _env("TENCENT_EXECUTOR_SSH_KEY")
        self.tencent_executor_compose_dir = _env("TENCENT_EXECUTOR_COMPOSE_DIR", "/opt/cameltv-tp/test-platform-v2/deploy")
        self.tencent_executor_release_dir = _env("TENCENT_EXECUTOR_RELEASE_DIR", "/opt/cameltv-release")
        self.tencent_executor_backup_dir = _env("TENCENT_EXECUTOR_BACKUP_DIR", "/opt/cameltv-backup")
        self.tencent_executor_image_backend = _env("TENCENT_EXECUTOR_IMAGE_BACKEND", "cameltv-tp-backend:latest")
        self.tencent_executor_image_frontend = _env("TENCENT_EXECUTOR_IMAGE_FRONTEND", "cameltv-tp-frontend:latest")
        self.tencent_executor_compose_project = _env("TENCENT_EXECUTOR_COMPOSE_PROJECT", "cameltv-tp-production")
        self.tencent_executor_timeout = int(_env("TENCENT_EXECUTOR_TIMEOUT", "600"))
        self.tencent_executor_keep_backups = int(_env("TENCENT_EXECUTOR_KEEP_BACKUPS", "7"))
        self.console_token = _env("RELEASE_CONSOLE_TOKEN")


settings = ConsoleSettings()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _store_conn() -> sqlite3.Connection:
    if not settings.release_control_database_path:
        raise HTTPException(503, "release-control 状态库未配置")
    path = Path(settings.release_control_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS releases (
    release_id TEXT PRIMARY KEY,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    manifest_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deployments (
    id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES releases(release_id),
    manifest_sha256 TEXT NOT NULL,
    environment TEXT NOT NULL,
    state TEXT NOT NULL,
    actor TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(environment, idempotency_key)
);
CREATE TABLE IF NOT EXISTS environment_locks (
    environment TEXT PRIMARY KEY,
    deployment_id TEXT NOT NULL REFERENCES deployments(id)
);
CREATE TABLE IF NOT EXISTS deployment_events (
    deployment_id TEXT NOT NULL REFERENCES deployments(id),
    sequence INTEGER NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    phase TEXT NOT NULL,
    reason TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (deployment_id, sequence)
);
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def _event_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _transition_state(
    deployment_id: str,
    from_state: str,
    to_state: str,
    phase: str,
    actor: str,
    reason: str,
) -> bool:
    with _store_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT state FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
        if row is None or row["state"] != from_state:
            return False
        conn.execute("UPDATE deployments SET state = ? WHERE id = ?", (to_state, deployment_id))
        seq = int(
            conn.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM deployment_events WHERE deployment_id = ?",
                (deployment_id,),
            ).fetchone()[0]  # noqa: E501
        )
        conn.execute(
            "INSERT INTO deployment_events(deployment_id, sequence, from_state, to_state, phase, reason, actor, created_at, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
            (
                deployment_id,
                seq,
                from_state,
                to_state,
                phase,
                reason,
                actor,
                _now_iso(),
                _event_hash(
                    {
                        "deployment_id": deployment_id,
                        "from_state": from_state,
                        "to_state": to_state,
                        "phase": phase,
                        "reason": reason,
                        "actor": actor,
                    }
                ),
            ),
        )
        if to_state in {
            "TEST_VERIFIED",
            "TEST_FAILED",
            "TEST_ROLLED_BACK",
            "PRODUCTION_VERIFIED",
            "PROD_FAILED",
            "PROD_ROLLED_BACK",
            "CANCELLED",
        }:
            conn.execute("DELETE FROM environment_locks WHERE deployment_id = ?", (deployment_id,))
        conn.commit()
    return True


def _require_token(authorization: str | None) -> None:
    """Validate Bearer token; fail closed when console token is unset."""
    if not settings.console_token:
        raise HTTPException(503, "RELEASE_CONSOLE_TOKEN 未配置（安全失败）")
    if authorization != f"Bearer {settings.console_token}":
        raise HTTPException(401, "Token 无效")


# ── models ────────────────────────────────────────────────────────────────


class SubmitReleaseIn(BaseModel):
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,127}$")
    image_tag: str = Field(min_length=1, max_length=64)
    manifest_json: str = Field(min_length=1)
    note: str = Field(default="", max_length=500)


class PublishIn(BaseModel):
    image_tag: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=500)


class RollbackIn(BaseModel):
    image_tag: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=500)


class ActionOut(BaseModel):
    action: str
    ok: bool
    summary: str
    logs: str = ""
    deployment_id: str = ""
    state: str = ""
    backups: list[dict] = Field(default_factory=list)


def _executor():
    try:
        return build_executor_from_settings(settings)
    except ExecutorNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc


# ── read API ──────────────────────────────────────────────────────────────


@app.get("/api/deployments")
def list_deployments(authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, release_id, manifest_sha256, environment, state, created_at "
            "FROM deployments ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/deployments/{deployment_id}/events")
def list_events(deployment_id: str, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT state FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "发布记录不存在")
        events = conn.execute(
            "SELECT sequence, from_state, to_state, phase, reason, actor, created_at "
            "FROM deployment_events WHERE deployment_id = ? ORDER BY sequence",
            (deployment_id,),
        ).fetchall()
    return [dict(e) for e in events]


# ── write API ─────────────────────────────────────────────────────────────


@app.post("/api/deployments")
def submit_release(body: SubmitReleaseIn, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        manifest_sha256 = hashlib.sha256(body.manifest_json.encode("utf-8")).hexdigest()
        deployment_id = uuid4().hex
        try:
            conn.execute(
                "INSERT OR IGNORE INTO releases(release_id, manifest_sha256, manifest_json, created_at) VALUES (?, ?, ?, ?)",  # noqa: E501
                (body.release_id, manifest_sha256, body.manifest_json, _now_iso()),
            )
            conn.execute(
                "INSERT INTO deployments(id, release_id, manifest_sha256, environment, state, actor, idempotency_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
                (deployment_id, body.release_id, manifest_sha256, "production", "DRAFT", "console", uuid4().hex, _now_iso()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO environment_locks(environment, deployment_id) VALUES (?, ?)",
                ("production", deployment_id),
            )
            conn.execute(
                "INSERT INTO deployment_events(deployment_id, sequence, from_state, to_state, phase, reason, actor, created_at, event_hash) VALUES (?, 1, '', 'DRAFT', 'register', ?, ?, ?, ?)",  # noqa: E501
                (
                    deployment_id,
                    f"production deployment registered: {body.release_id}",
                    "console",
                    _now_iso(),
                    _event_hash(
                        {
                            "deployment_id": deployment_id,
                            "from_state": "",
                            "to_state": "DRAFT",
                            "phase": "register",
                            "reason": f"production deployment registered: {body.release_id}",
                            "actor": "console",
                        }
                    ),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(409, f"登记冲突: {exc}") from exc
    return ActionOut(
        action="submit",
        ok=True,
        summary=f"release {body.release_id} registered (production)",
        deployment_id=deployment_id,
        state="DRAFT",
    )


@app.post("/api/deployments/{deployment_id}/validate")
def validate_deployment(deployment_id: str, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    """DRAFT → VALIDATED：不可变 manifest 结构校验（ADR-0015 门禁）。"""
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT r.release_id AS release_id, r.manifest_json AS manifest_json, d.state AS state "
            "FROM deployments d JOIN releases r ON r.release_id = d.release_id WHERE d.id = ?",
            (deployment_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "发布记录不存在")
    if row["state"] != "DRAFT":
        raise HTTPException(409, f"当前状态 {row['state']} 不允许验证")
    try:
        manifest = json.loads(row["manifest_json"])
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"manifest 不是合法 JSON: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise HTTPException(422, "manifest schema_version 必须为 1.0")
    if manifest.get("release_id") != row["release_id"]:
        raise HTTPException(422, "manifest release_id 与登记记录不一致")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("git_sha", ""))):
        raise HTTPException(422, "manifest git_sha 必须是 40 位 hex")
    for side in ("frontend", "backend"):
        digest = str((manifest.get(side) or {}).get("digest", ""))
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise HTTPException(422, f"manifest {side}.digest 必须是 sha256:<64 位 hex>")
    if not _transition_state(deployment_id, "DRAFT", "VALIDATED", "validate", "console", "manifest validated"):
        raise HTTPException(409, "状态已变化，验证失败")
    return ActionOut(
        action="validate",
        ok=True,
        summary=f"release {row['release_id']} validated",
        deployment_id=deployment_id,
        state="VALIDATED",
    )


@app.post("/api/deployments/{deployment_id}/publish")
def publish_deployment(deployment_id: str, body: PublishIn, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT state FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "发布记录不存在")
    if row["state"] not in {"VALIDATED", "TEST_VERIFIED"}:
        raise HTTPException(409, f"当前状态 {row['state']} 不允许发布")

    executor = _executor()
    try:
        result = executor.deploy(body.image_tag)
    except ExecutorCommandFailed as exc:
        raise HTTPException(500, f"发布执行失败: {exc}") from exc

    try:
        _transition_state(deployment_id, row["state"], "PROD_DEPLOYING", "deploy", "console", "publish started")
        _transition_state(deployment_id, "PROD_DEPLOYING", "PROD_OBSERVING", "deploy", "console", "publish succeeded")
    except Exception:
        pass
    return ActionOut(
        action="publish",
        ok=True,
        summary=result.summary,
        logs=result.logs,
        deployment_id=deployment_id,
        state="PROD_OBSERVING",
    )


@app.post("/api/deployments/{deployment_id}/verify")
def verify_deployment(deployment_id: str, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    """PROD_OBSERVING → PRODUCTION_VERIFIED：执行线上健康检查后确认上线。"""
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT state FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "发布记录不存在")
    if row["state"] != "PROD_OBSERVING":
        raise HTTPException(409, f"当前状态 {row['state']} 不允许确认上线")
    executor = _executor()
    try:
        result = executor.health()
    except ExecutorCommandFailed as exc:
        raise HTTPException(500, f"上线健康检查失败: {exc}") from exc
    if not _transition_state(deployment_id, "PROD_OBSERVING", "PRODUCTION_VERIFIED", "verify", "console", "production health ok"):
        raise HTTPException(409, "状态已变化，确认上线失败")
    return ActionOut(
        action="verify",
        ok=True,
        summary="production verified (health ok)",
        logs=result.logs,
        deployment_id=deployment_id,
        state="PRODUCTION_VERIFIED",
    )


@app.post("/api/deployments/{deployment_id}/rollback")
def rollback_deployment(deployment_id: str, body: RollbackIn, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    with _store_conn() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT state FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "发布记录不存在")

    executor = _executor()
    try:
        result = executor.rollback(body.image_tag)
    except ExecutorCommandFailed as exc:
        raise HTTPException(500, f"回滚执行失败: {exc}") from exc

    try:
        _transition_state(deployment_id, row["state"], "PROD_ROLLING_BACK", "rollback", "console", "rollback started")
        _transition_state(deployment_id, "PROD_ROLLING_BACK", "PROD_ROLLED_BACK", "rollback", "console", "rollback succeeded")
    except Exception:
        pass
    return ActionOut(
        action="rollback",
        ok=True,
        summary=result.summary,
        logs=result.logs,
        deployment_id=deployment_id,
        state="PROD_ROLLED_BACK",
    )


@app.post("/api/deployments/{deployment_id}/backup")
def backup_database(deployment_id: str, authorization: str | None = Header(None, alias="Authorization", include_in_schema=False)):
    _require_token(authorization)
    executor = _executor()
    try:
        result = executor.backup()
    except ExecutorCommandFailed as exc:
        raise HTTPException(500, f"备份执行失败: {exc}") from exc
    return ActionOut(
        action="backup",
        ok=True,
        summary=result.summary,
        logs=result.logs,
        deployment_id=deployment_id,
        backups=[{"filename": f} for f in result.artifacts],
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "console": "release-console"}


# ── static frontend ───────────────────────────────────────────────────────

_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="console-ui")
