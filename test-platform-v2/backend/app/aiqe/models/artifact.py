"""M1 / TA-007 + AUD-008：Run Artifact 模型（13 号 §4.12）。

- 存储只存 URI + sha256，不存二进制；
- `linked_evidence_type + linked_evidence_id` 跨源引用蓝湖证据（不复制文件）；
- `redaction_status`：pending → sanitized / rejected（单向）；
- AUD-008 起增加上传生命周期：`PENDING_UPLOAD → AVAILABLE | CORRUPTED | FAILED`，
  过期清理改为**墓碑**（`PURGED` + `deleted_at`），元数据保留审计。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ArtifactType(StrEnum):
    """v1.5 §02 AUD-008 规定的最小类型集合（原小写旧值继续接受）。"""

    SCREENSHOT = "SCREENSHOT"
    VIDEO = "VIDEO"
    PLAYWRIGHT_TRACE = "PLAYWRIGHT_TRACE"
    HAR = "HAR"
    DOM_SNAPSHOT = "DOM_SNAPSHOT"
    ACCESSIBILITY_TREE = "ACCESSIBILITY_TREE"
    HTTP_REQUEST = "HTTP_REQUEST"
    HTTP_RESPONSE = "HTTP_RESPONSE"
    DB_RESULT_SUMMARY = "DB_RESULT_SUMMARY"
    CONSOLE_LOG = "CONSOLE_LOG"
    RUNNER_LOG = "RUNNER_LOG"
    DEVICE_LOG = "DEVICE_LOG"
    NETWORK_PROFILE = "NETWORK_PROFILE"
    ENVIRONMENT_SNAPSHOT = "ENVIRONMENT_SNAPSHOT"


class ArtifactUploadStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    AVAILABLE = "AVAILABLE"
    CORRUPTED = "CORRUPTED"
    FAILED = "FAILED"
    PURGED = "PURGED"


class RunArtifact(Base):
    __tablename__ = "run_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=True, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_runs.id", ondelete="SET NULL"), nullable=True
    )
    step_attempt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("step_attempts.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/octet-stream"
    )
    redaction_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    upload_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="AVAILABLE"
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_scope: Mapped[str] = mapped_column(String(16), nullable=False, default="project")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    linked_evidence_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    linked_evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_run_artifacts_run_created", "run_id", "created_at"),
        Index("ix_run_artifacts_sha256", "sha256"),
        Index("ix_run_artifacts_redaction", "redaction_status"),
        Index("ix_run_artifacts_node_run", "node_run_id"),
        Index("ix_run_artifacts_upload_status", "upload_status"),
    )
