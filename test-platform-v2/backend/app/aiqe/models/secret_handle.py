"""AUD-003：Secret Handle 元信息（表 ``aiqe_secret_handles``）。

**只保存 Secret Manager / 进程内 Vault 的引用，绝不保存密钥明文**（v1.5 §06 3.1）。
Scope 绑定 ``project_id / run_id / producer_node_run_id / allowed_consumer_nodes / expires_at``，
下游节点只能通过受控 resolver 取值。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SecretHandle(Base):
    __tablename__ = "aiqe_secret_handles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producer_node_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("node_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Vault 引用（`vault://<handle_id>` 或外部 Secret Manager 路径），不含明文。
    secret_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    key_name: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed_consumer_nodes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_secret_handles_scope", "project_id", "run_id", "expires_at"),
    )
