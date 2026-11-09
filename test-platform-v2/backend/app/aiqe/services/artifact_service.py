"""M1 / TA-007：Artifact Manager（13 号 §4.12）。

- 上传：sha256 去重（同一内容只落一份文件，多行可共享 URI）；
- 权限：所有读写按 `run.project_id` 校验，跨项目 403（`ArtifactAccessDenied`）；
- 脱敏：`redaction_status` pending → sanitized / rejected 单向；
- 跨源引用：`linked_evidence_type + linked_evidence_id` 成对写入，不复制文件。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.run import TestRun
from app.aiqe.services.artifact_storage import (
    ArtifactStorageBackend,
    ArtifactStorageError,
    LocalArtifactStorage,
)

ARTIFACT_TYPES: frozenset[str] = frozenset(
    {
        "screenshot",
        "video",
        "trace",
        "har",
        "log",
        "request",
        "response",
        "dom",
        "a11y",
        "report",
        "db_snapshot",
        "other",
    }
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


class ArtifactAccessDenied(PermissionError):
    """跨项目访问（HTTP 层映射 403）。"""


class InvalidArtifact(ValueError):
    """非法 artifact 参数/状态迁移。"""


def _run_or_deny(db: Session, run_id: str, project_id: int) -> TestRun:
    run = db.get(TestRun, run_id)
    if run is None:
        raise InvalidArtifact(f"run 不存在: {run_id}")
    if run.project_id != project_id:
        raise ArtifactAccessDenied("artifact 不属于当前项目")
    return run


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
    linked_evidence_type: str | None = None,
    linked_evidence_id: str | None = None,
    storage: ArtifactStorageBackend | None = None,
) -> RunArtifact:
    _run_or_deny(db, run_id, project_id)
    if artifact_type not in ARTIFACT_TYPES:
        raise InvalidArtifact(f"未知 artifact_type: {artifact_type!r}")
    if (linked_evidence_type is None) != (linked_evidence_id is None):
        raise InvalidArtifact("linked_evidence_type/id 必须成对出现")
    if linked_evidence_type is not None and linked_evidence_type not in LINKED_EVIDENCE_TYPES:
        raise InvalidArtifact(f"未知 linked_evidence_type: {linked_evidence_type!r}")
    if len(content) > MAX_ARTIFACT_BYTES:
        raise InvalidArtifact(f"artifact 超过 {MAX_ARTIFACT_BYTES} bytes 限制")

    digest = hashlib.sha256(content).hexdigest()
    backend = storage or LocalArtifactStorage()
    uri = backend.put(content, digest)
    row = RunArtifact(
        run_id=run_id,
        node_run_id=node_run_id,
        step_attempt_id=step_attempt_id,
        artifact_type=artifact_type,
        storage_uri=uri,
        sha256=digest,
        size_bytes=len(content),
        mime_type=mime_type,
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
    backend = storage or LocalArtifactStorage()
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
