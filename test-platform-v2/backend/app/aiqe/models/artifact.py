"""M1 / TA-007：Run Artifact 模型（13 号 §4.12）。

- 存储只存 URI + sha256，不存二进制；
- `linked_evidence_type + linked_evidence_id` 跨源引用蓝湖证据（不复制文件）；
- `redaction_status`：pending → sanitized / rejected（单向）。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RunArtifact(Base):
    __tablename__ = "run_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_runs.id", ondelete="SET NULL"), nullable=True
    )
    step_attempt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("step_attempts.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(String(24), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/octet-stream"
    )
    redaction_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
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
    )
