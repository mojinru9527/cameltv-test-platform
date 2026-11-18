"""M1 / TA-007 + AUD-008：Artifact Manager（13 号 §4.12）。

- 上传：sha256 去重（同一内容只落一份文件，多行可共享 URI）；
- 权限：所有读写按 `run.project_id` 校验，跨项目 403（`ArtifactAccessDenied`）；
- 脱敏：`redaction_status` pending → sanitized / rejected 单向；
- 跨源引用：`linked_evidence_type + linked_evidence_id` 成对写入，不复制文件；
- AUD-008：两阶段上传（`PENDING_UPLOAD → AVAILABLE/CORRUPTED`），服务端重算 sha256，
  下载前重新鉴权，保留期 + 墓碑删除（`PURGED`）。
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import (
    ArtifactType,
    ArtifactUploadStatus,
    RunArtifact,
)
from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services.artifact_storage import (
    ArtifactStorageBackend,
    ArtifactStorageError,
    LocalArtifactStorage,
    get_storage_backend,
)

#: 旧小写类型 → v1.5 规范类型（保持既有调用与存储兼容）。
LEGACY_TYPE_ALIASES: dict[str, str] = {
    "screenshot": ArtifactType.SCREENSHOT.value,
    "video": ArtifactType.VIDEO.value,
    "trace": ArtifactType.PLAYWRIGHT_TRACE.value,
    "har": ArtifactType.HAR.value,
    "log": ArtifactType.RUNNER_LOG.value,
    "request": ArtifactType.HTTP_REQUEST.value,
    "response": ArtifactType.HTTP_RESPONSE.value,
    "dom": ArtifactType.DOM_SNAPSHOT.value,
    "a11y": ArtifactType.ACCESSIBILITY_TREE.value,
    "report": ArtifactType.RUNNER_LOG.value,
    "db_snapshot": ArtifactType.DB_RESULT_SUMMARY.value,
    "other": ArtifactType.RUNNER_LOG.value,
}
ARTIFACT_TYPES: frozenset[str] = frozenset(
    {item.value for item in ArtifactType} | set(LEGACY_TYPE_ALIASES)
)
LINKED_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {"lanhu_evidence", "defect", "external_url"}
)
REDACTION_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"sanitized", "rejected"}),
    "sanitized": frozenset(),
    "rejected": frozenset(),
}
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
DEFAULT_RETENTION_DAYS = 30
MAX_RETENTION_DAYS = 365


class ArtifactAccessDenied(PermissionError):
    """跨项目访问（HTTP 层映射 403）。"""


class InvalidArtifact(ValueError):
    """非法 artifact 参数/状态迁移。"""


def canonical_type(artifact_type: str) -> str:
    raw = str(artifact_type or "").strip()
    if raw in LEGACY_TYPE_ALIASES:
        return LEGACY_TYPE_ALIASES[raw]
    if raw in ARTIFACT_TYPES:
        return raw
    raise InvalidArtifact(f"未知 artifact_type: {artifact_type!r}")


def _run_or_deny(db: Session, run_id: str, project_id: int) -> TestRun:
    run = db.get(TestRun, run_id)
    if run is None:
        raise InvalidArtifact(f"run 不存在: {run_id}")
    if run.project_id != project_id:
        raise ArtifactAccessDenied("artifact 不属于当前项目")
    return run


def _retention_until(days: int | None, now: datetime) -> datetime:
    value = DEFAULT_RETENTION_DAYS if days is None else int(days)
    if not 1 <= value <= MAX_RETENTION_DAYS:
        raise InvalidArtifact(f"retention_days 必须在 1..{MAX_RETENTION_DAYS}")
    return now + timedelta(days=value)


def create_pending_artifact(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    artifact_type: str,
    content_type: str = "application/octet-stream",
    node_run_id: str | None = None,
    step_attempt_id: str | None = None,
    expected_sha256: str | None = None,
    expected_size_bytes: int | None = None,
    metadata: dict[str, Any] | None = None,
    retention_days: int | None = None,
    access_scope: str = "project",
    now: datetime | None = None,
) -> tuple[RunArtifact, dict[str, Any]]:
    """创建上传会话；上传完成前 `upload_status=PENDING_UPLOAD`。"""
    run = _run_or_deny(db, run_id, project_id)
    canonical = canonical_type(artifact_type)
    if node_run_id is not None:
        node = db.get(NodeRun, node_run_id)
        if node is None or node.run_id != run.id:
            raise InvalidArtifact("node_run 不属于该 Run")
    if step_attempt_id is not None:
        attempt = db.get(StepAttempt, step_attempt_id)
        if attempt is None:
            raise InvalidArtifact("step_attempt 不存在")
    if expected_size_bytes is not None and int(expected_size_bytes) > MAX_ARTIFACT_BYTES:
        raise InvalidArtifact(f"artifact 超过 {MAX_ARTIFACT_BYTES} bytes 限制")
    moment = now or datetime.now(UTC)
    row = RunArtifact(
        id=str(uuid.uuid4()),
        project_id=int(project_id),
        run_id=run.id,
        node_run_id=node_run_id,
        step_attempt_id=step_attempt_id,
        artifact_type=canonical,
        storage_uri="",
        sha256="",
        expected_sha256=(str(expected_sha256).lower() if expected_sha256 else None),
        size_bytes=int(expected_size_bytes or 0),
        mime_type=content_type or "application/octet-stream",
        redaction_status="pending",
        upload_status=ArtifactUploadStatus.PENDING_UPLOAD.value,
        retention_until=_retention_until(retention_days, moment),
        access_scope=str(access_scope or "project"),
        metadata_json=dict(metadata or {}),
    )
    db.add(row)
    db.flush()
    target = {
        "artifact_id": row.id,
        "upload_url": f"/api/v1/aiqe/artifacts/{row.id}/content",
        "method": "PUT",
        "content_type": row.mime_type,
        "expires_at": (moment + timedelta(minutes=30)).isoformat(),
        "max_bytes": MAX_ARTIFACT_BYTES,
    }
    return row, target


def complete_upload(
    db: Session,
    *,
    artifact_id: str,
    project_id: int,
    content: bytes,
    storage: ArtifactStorageBackend | None = None,
    now: datetime | None = None,
) -> RunArtifact:
    """完成上传：服务端重算 sha256，不匹配标记 CORRUPTED 且不落存储。"""
    row = get_artifact(db, artifact_id, project_id)
    if row.upload_status != ArtifactUploadStatus.PENDING_UPLOAD.value:
        raise InvalidArtifact(f"artifact 状态不是 PENDING_UPLOAD: {row.upload_status}")
    if not content:
        row.upload_status = ArtifactUploadStatus.FAILED.value
        db.flush()
        raise InvalidArtifact("上传内容为空")
    if len(content) > MAX_ARTIFACT_BYTES:
        row.upload_status = ArtifactUploadStatus.FAILED.value
        db.flush()
        raise InvalidArtifact(f"artifact 超过 {MAX_ARTIFACT_BYTES} bytes 限制")

    digest = hashlib.sha256(content).hexdigest()
    if row.expected_sha256 and row.expected_sha256 != digest:
        row.upload_status = ArtifactUploadStatus.CORRUPTED.value
        row.sha256 = digest
        row.metadata_json = {
            **(row.metadata_json or {}),
            "corruption": {
                "expected_sha256": row.expected_sha256,
                "actual_sha256": digest,
                "detected_at": (now or datetime.now(UTC)).isoformat(),
            },
        }
        db.flush()
        raise InvalidArtifact("sha256 校验失败：artifact 标记 CORRUPTED")

    backend = storage or get_storage_backend()
    uri = backend.put(content, digest)
    row.storage_uri = uri
    row.sha256 = digest
    row.size_bytes = len(content)
    row.upload_status = ArtifactUploadStatus.AVAILABLE.value
    db.flush()
    return row


def open_download(
    db: Session,
    *,
    artifact_id: str,
    project_id: int,
    storage: ArtifactStorageBackend | None = None,
) -> tuple[RunArtifact, bytes]:
    """下载前重新鉴权；未完成上传/已损坏/已清理一律拒绝。"""
    row = get_artifact(db, artifact_id, project_id)
    if row.upload_status == ArtifactUploadStatus.PURGED.value:
        raise InvalidArtifact("artifact 已按保留策略清理（仅保留审计墓碑）")
    if row.upload_status == ArtifactUploadStatus.PENDING_UPLOAD.value:
        raise InvalidArtifact("artifact 上传未完成，不提供下载")
    if row.upload_status in {
        ArtifactUploadStatus.CORRUPTED.value,
        ArtifactUploadStatus.FAILED.value,
    }:
        raise InvalidArtifact(f"artifact 不可用: {row.upload_status}")
    backend = storage
    if backend is None:
        backend = (
            LocalArtifactStorage()
            if row.storage_uri.startswith("file://")
            else get_storage_backend()
        )
    return row, backend.read(row.storage_uri)


def verify_integrity(
    db: Session,
    artifact_id: str,
    project_id: int,
    *,
    storage: ArtifactStorageBackend | None = None,
) -> RunArtifact:
    """读取存储并重新校验 sha256；不匹配标记 CORRUPTED。"""
    row = get_artifact(db, artifact_id, project_id)
    backend = storage or get_storage_backend()
    try:
        content = backend.read(row.storage_uri)
    except ArtifactStorageError:
        row.upload_status = ArtifactUploadStatus.CORRUPTED.value
        db.flush()
        raise
    digest = hashlib.sha256(content).hexdigest()
    if digest != row.sha256:
        row.upload_status = ArtifactUploadStatus.CORRUPTED.value
        row.metadata_json = {
            **(row.metadata_json or {}),
            "corruption": {"expected_sha256": row.sha256, "actual_sha256": digest},
        }
    db.flush()
    return row


def incompleteness_reasons(db: Session, run_id: str) -> list[str]:
    """Run 证据是否完整（AUD-008 §10：PENDING_UPLOAD 时 P0 不得汇总为 PASS）。"""
    rows = list(
        db.scalars(
            select(RunArtifact).where(
                RunArtifact.run_id == run_id,
                RunArtifact.upload_status.in_(
                    [
                        ArtifactUploadStatus.PENDING_UPLOAD.value,
                        ArtifactUploadStatus.CORRUPTED.value,
                    ]
                ),
            )
        )
    )
    reasons = [
        f"{row.artifact_type}:{row.upload_status}:{row.id}" for row in rows
    ]
    return reasons


def put_artifact(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    content: bytes,
    artifact_type: str,
    mime_type: str = "application/octet-stream",
    node_run_id: str | None = None,
    step_attempt_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    redaction_status: str = "pending",
    linked_evidence_type: str | None = None,
    linked_evidence_id: str | None = None,
    storage: ArtifactStorageBackend | None = None,
) -> RunArtifact:
    """单步上传（内部/旧路径）：直接落库并置 AVAILABLE。"""
    _run_or_deny(db, run_id, project_id)
    canonical = canonical_type(artifact_type)
    if (linked_evidence_type is None) != (linked_evidence_id is None):
        raise InvalidArtifact("linked_evidence_type/id 必须成对出现")
    if linked_evidence_type is not None and linked_evidence_type not in LINKED_EVIDENCE_TYPES:
        raise InvalidArtifact(f"未知 linked_evidence_type: {linked_evidence_type!r}")
    if len(content) > MAX_ARTIFACT_BYTES:
        raise InvalidArtifact(f"artifact 超过 {MAX_ARTIFACT_BYTES} bytes 限制")

    digest = hashlib.sha256(content).hexdigest()
    backend = storage or get_storage_backend()
    uri = backend.put(content, digest)
    row = RunArtifact(
        project_id=int(project_id),
        run_id=run_id,
        node_run_id=node_run_id,
        step_attempt_id=step_attempt_id,
        artifact_type=canonical,
        storage_uri=uri,
        sha256=digest,
        size_bytes=len(content),
        mime_type=mime_type,
        upload_status=ArtifactUploadStatus.AVAILABLE.value,
        metadata_json=metadata or {},
        linked_evidence_type=linked_evidence_type,
        linked_evidence_id=linked_evidence_id,
    )
    db.add(row)
    db.flush()
    return row


def get_artifact(db: Session, artifact_id: str, project_id: int) -> RunArtifact:
    row = db.get(RunArtifact, artifact_id)
    if row is None:
        raise InvalidArtifact("artifact 不存在")
    _run_or_deny(db, row.run_id, project_id)
    return row


def list_artifacts(
    db: Session, run_id: str, project_id: int, *, limit: int = 200
) -> list[RunArtifact]:
    _run_or_deny(db, run_id, project_id)
    limit = max(1, min(int(limit), 1000))
    return list(
        db.scalars(
            select(RunArtifact)
            .where(RunArtifact.run_id == run_id)
            .order_by(RunArtifact.created_at.desc())
            .limit(limit)
        )
    )


def read_artifact(
    db: Session,
    artifact_id: str,
    project_id: int,
    *,
    storage: ArtifactStorageBackend | None = None,
) -> bytes:
    row = get_artifact(db, artifact_id, project_id)
    if storage is None:
        backend = LocalArtifactStorage() if row.storage_uri.startswith("file://") else get_storage_backend()
    else:
        backend = storage
    try:
        return backend.read(row.storage_uri)
    except ArtifactStorageError:
        raise
    except OSError as exc:  # pragma: no cover - IO 兜底
        raise ArtifactStorageError(f"读取 artifact 失败: {exc}") from exc


def mark_redaction(
    db: Session, artifact_id: str, project_id: int, status: str
) -> RunArtifact:
    row = get_artifact(db, artifact_id, project_id)
    allowed = REDACTION_TRANSITIONS.get(row.redaction_status, frozenset())
    if status not in allowed:
        raise InvalidArtifact(f"非法脱敏状态迁移: {row.redaction_status} → {status}")
    row.redaction_status = status
    db.flush()
    return row


def storage_root() -> Path:
    return Path("storage") / "artifacts"
