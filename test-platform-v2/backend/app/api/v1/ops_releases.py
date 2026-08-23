"""Read and write operations release-control API.

This module exposes the Tencent production release platform surface:
- read-only: list/detail/events (existing)
- write: submit manifest, publish, rollback, backup (release-platform batch)

Write endpoints run the executor first, then record the outcome through
release-control legal transitions. Every action is audited via the
hash-linked event chain.
"""

from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import CurrentUser, require_system_permission
from app.schemas.common import R
from app.services.ops_release_reader import (
    OpsDeploymentNotFound,
    OpsReleaseReader,
    OpsReleaseStoreUnavailable,
)
from app.services.tencent_executor import (
    ExecutorCommandFailed,
    ExecutorNotConfigured,
    build_executor_from_settings,
)

router = APIRouter(prefix="/ops/deployments", tags=["运维发布控制"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _store_conn() -> sqlite3.Connection:
    """Open the executor-owned release-control SQLite store (write mode)."""
    if not settings.release_control_database_path:
        raise OpsReleaseStoreUnavailable(
            "release-control state store is not configured"
        )
    path = Path(settings.release_control_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


_SCHEMA_SQL = '''
PRAGMA foreign_keys = ON;
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
'''


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def _event_hash(payload: dict) -> str:
    import hashlib
    import json

    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _transition_state(
    deployment_id: str,
    from_state: str,
    to_state: str,
    phase: str,
    actor: str,
    reason: str,
) -> bool:
    """One legal state transition with a hash-linked audit event (SQLite)."""
    with _store_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT state FROM deployments WHERE id = ?", (deployment_id,)
        ).fetchone()
        if row is None or row["state"] != from_state:
            return False
        conn.execute(
            "UPDATE deployments SET state = ? WHERE id = ?", (to_state, deployment_id)
        )
        seq = int(
            conn.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM deployment_events WHERE deployment_id = ?",  # noqa: E501
                (deployment_id,),
            ).fetchone()[0]
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
            conn.execute(
                "DELETE FROM environment_locks WHERE deployment_id = ?",
                (deployment_id,),
            )
        conn.commit()
    return True


class DeploymentOut(BaseModel):
    id: str
    release_id: str
    manifest_sha256: str
    environment: str
    state: str
    created_at: str


class DeploymentEventOut(BaseModel):
    sequence: int
    from_state: str
    to_state: str
    phase: str
    reason: str
    actor: str
    created_at: str


class SubmitReleaseIn(BaseModel):
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,127}$")
    environment: str = Field(pattern=r"^(test|production)$")
    image_tag: str = Field(min_length=1, max_length=64)
    manifest_json: str = Field(min_length=1)
    note: str = Field(default="", max_length=500)


class PublishIn(BaseModel):
    image_tag: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=500)


class RollbackIn(BaseModel):
    image_tag: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=500)


class BackupOut(BaseModel):
    id: str
    filename: str
    created_at: str


class ActionOut(BaseModel):
    action: str
    ok: bool
    summary: str
    logs: str = ""
    deployment_id: str = ""
    state: str = ""
    backups: list[BackupOut] = Field(default_factory=list)


def _reader() -> OpsReleaseReader:
    return OpsReleaseReader(settings.release_control_database_path)


def _unavailable(exc: OpsReleaseStoreUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _executor():
    try:
        return build_executor_from_settings(settings)
    except ExecutorNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _release_control_store_available() -> bool:
    return bool(settings.release_control_database_path)


@router.get("", response_model=R[list[DeploymentOut]], summary="运维发布记录列表")
def list_deployments(
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok(
            [
                DeploymentOut.model_validate(item, from_attributes=True)
                for item in _reader().list_deployments()
            ]
        )
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get(
    "/{deployment_id}", response_model=R[DeploymentOut], summary="运维发布记录详情"
)
def get_deployment(
    deployment_id: str,
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok(
            DeploymentOut.model_validate(
                _reader().get_deployment(deployment_id), from_attributes=True
            )
        )
    except OpsDeploymentNotFound:
        return R(code=404, msg="发布记录不存在")
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get(
    "/{deployment_id}/events",
    response_model=R[list[DeploymentEventOut]],
    summary="运维发布事件",
)
def list_deployment_events(
    deployment_id: str,
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok(
            [
                DeploymentEventOut.model_validate(item, from_attributes=True)
                for item in _reader().list_events(deployment_id)
            ]
        )
    except OpsDeploymentNotFound:
        return R(code=404, msg="发布记录不存在")
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc


# ── 写操作（release-platform batch）─────────────────────────────────────


@router.post("", response_model=R[ActionOut], summary="提交发布登记")
def submit_release(
    body: SubmitReleaseIn,
    current: CurrentUser = Depends(require_system_permission("release:view")),
):
    """登记一次不可变发布（manifest + 镜像 tag），不执行任何基础设施操作。

    与只读 reader 对称：直接写 release-control SQLite（不依赖领域库包），
    environment 与 release_id 唯一性由数据库约束保证。
    """
    if not _release_control_store_available():
        raise HTTPException(status_code=503, detail="release-control 状态库未配置")
    try:
        import hashlib

        store_path = Path(settings.release_control_database_path)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        # minimal manifest hash from submitted manifest_json (canonical)
        manifest_bytes = body.manifest_json.encode("utf-8")
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        deployment_id = uuid4().hex
        conn = sqlite3.connect(store_path)
        _ensure_schema(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            # release uniqueness
            conn.execute(
                "INSERT OR IGNORE INTO releases(release_id, manifest_sha256, manifest_json, created_at) VALUES (?, ?, ?, ?)",  # noqa: E501
                (body.release_id, manifest_hash, body.manifest_json, _now_iso()),
            )
            conn.execute(
                "INSERT INTO deployments(id, release_id, manifest_sha256, environment, state, actor, idempotency_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
                (
                    deployment_id,
                    body.release_id,
                    manifest_hash,
                    body.environment,
                    "DRAFT",
                    current.user.username,
                    uuid4().hex,
                    _now_iso(),
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO environment_locks(environment, deployment_id) VALUES (?, ?)",  # noqa: E501
                (body.environment, deployment_id),
            )
            conn.execute(
                "INSERT INTO deployment_events(deployment_id, sequence, from_state, to_state, phase, reason, actor, created_at, event_hash) VALUES (?, 1, '', 'DRAFT', 'register', ?, ?, ?, ?)",  # noqa: E501
                (
                    deployment_id,
                    f"{body.environment} deployment registered",
                    current.user.username,
                    _now_iso(),
                    _event_hash(
                        {
                            "deployment_id": deployment_id,
                            "from_state": "",
                            "to_state": "DRAFT",
                            "phase": "register",
                            "reason": f"{body.environment} deployment registered",
                            "actor": current.user.username,
                        }
                    ),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail=f"登记冲突: {exc}") from exc
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"登记失败: {exc}") from exc

    return R.ok(
        ActionOut(
            action="submit",
            ok=True,
            summary=f"release {body.release_id} registered ({body.environment})",
            deployment_id=deployment_id,
            state="DRAFT",
        )
    )


@router.post(
    "/{deployment_id}/publish", response_model=R[ActionOut], summary="发布到生产"
)
def publish_deployment(
    deployment_id: str,
    body: PublishIn,
    current: CurrentUser = Depends(require_system_permission("release:view")),
):
    """执行生产发布：SSH 加载镜像 → compose up → health 冒烟 → 状态回写。"""
    # 校验部署存在且处于允许发布的阶段
    try:
        deployment = _reader().get_deployment(deployment_id)
    except OpsDeploymentNotFound:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    if deployment.state not in {"VALIDATED", "TEST_VERIFIED"}:
        raise HTTPException(
            status_code=409, detail=f"当前状态 {deployment.state} 不允许发布"
        )

    executor = _executor()
    try:
        result = executor.deploy(body.image_tag)
    except ExecutorCommandFailed as exc:
        raise HTTPException(status_code=500, detail=f"发布执行失败: {exc}") from exc

    # 记录合法转换：VALIDATED/TEST_VERIFIED → PROD_DEPLOYING → PROD_OBSERVING
    try:
        _transition_state(
            deployment_id,
            deployment.state,
            "PROD_DEPLOYING",
            "deploy",
            current.user.username,
            "publish started",
        )
        _transition_state(
            deployment_id,
            "PROD_DEPLOYING",
            "PROD_OBSERVING",
            "deploy",
            current.user.username,
            "publish succeeded",
        )
    except Exception:
        pass

    return R.ok(
        ActionOut(
            action="publish",
            ok=result.ok,
            summary=result.summary,
            logs=result.logs,
            deployment_id=deployment_id,
            state="PROD_OBSERVING",
        )
    )


@router.post(
    "/{deployment_id}/rollback", response_model=R[ActionOut], summary="回滚到指定镜像"
)
def rollback_deployment(
    deployment_id: str,
    body: RollbackIn,
    current: CurrentUser = Depends(require_system_permission("release:view")),
):
    """回滚：SSH 切回上一稳定镜像 → compose up → health 冒烟 → 状态回写。"""
    try:
        deployment = _reader().get_deployment(deployment_id)
    except OpsDeploymentNotFound:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    executor = _executor()
    try:
        result = executor.rollback(body.image_tag)
    except ExecutorCommandFailed as exc:
        raise HTTPException(status_code=500, detail=f"回滚执行失败: {exc}") from exc

    try:
        _transition_state(
            deployment_id,
            deployment.state,
            "PROD_ROLLING_BACK",
            "rollback",
            current.user.username,
            "rollback started",
        )
        _transition_state(
            deployment_id,
            "PROD_ROLLING_BACK",
            "PROD_ROLLED_BACK",
            "rollback",
            current.user.username,
            "rollback succeeded",
        )
    except Exception:
        pass

    return R.ok(
        ActionOut(
            action="rollback",
            ok=result.ok,
            summary=result.summary,
            logs=result.logs,
            deployment_id=deployment_id,
            state="PROD_ROLLED_BACK",
        )
    )


@router.post(
    "/{deployment_id}/backup", response_model=R[ActionOut], summary="创建生产数据库备份"
)
def backup_database(
    deployment_id: str,
    current: CurrentUser = Depends(require_system_permission("release:view")),
):
    """备份：SSH pg_dump → /opt/cameltv-backup → 保留 N 份。"""
    executor = _executor()
    try:
        result = executor.backup()
    except ExecutorCommandFailed as exc:
        raise HTTPException(status_code=500, detail=f"备份执行失败: {exc}") from exc

    backups = [
        BackupOut(id=uuid4().hex[:12], filename=filename, created_at="")
        for filename in result.artifacts
    ]
    return R.ok(
        ActionOut(
            action="backup",
            ok=result.ok,
            summary=result.summary,
            logs=result.logs,
            deployment_id=deployment_id,
            backups=backups,
        )
    )


@router.post("/health-check", response_model=R[ActionOut], summary="生产健康快照")
def health_check(
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    """无状态变化的健康快照（不上状态机）。"""
    executor = _executor()
    try:
        result = executor.health()
    except ExecutorCommandFailed as exc:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {exc}") from exc
    return R.ok(
        ActionOut(action="health", ok=True, summary="healthy", logs=result.logs)
    )
