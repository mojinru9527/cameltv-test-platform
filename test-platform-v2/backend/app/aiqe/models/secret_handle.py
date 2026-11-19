"""AUD-003：Secret Handle 元信息（表 ``aiqe_secret_handles``）。

**只保存 Secret Manager / 进程内 Vault 的引用，绝不保存密钥明文**（v1.5 §06 3.1）。
Scope 绑定 ``project_id / run_id / producer_node_run_id / allowed_consumer_nodes / expires_at``，
下游节点只能通过受控 resolver 取值。

V16-003 扩展字段（规格 §9.3）：
- ``secret_type``：jwt / api_key / cookie / password / generic；
- ``key_version`` / ``rotation_version``：密钥轮换与版本；
- ``consumer_scope_json``：结构化 consumer scope（节点/角色/过期策略），
  与 ``allowed_consumer_nodes`` 并存以兼容旧数据；
- ``access_audit_id`` / ``access_count`` / ``last_accessed_at``：访问审计。
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
    secret_type: Mapped[str] = mapped_column(String(32), nullable=False, default="generic")
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rotation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allowed_consumer_nodes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    consumer_scope_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    access_audit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_secret_handles_scope", "project_id", "run_id", "expires_at"),
    )


class SecretAccessAudit(Base):
    """Handle 解析审计：成功/拒绝都记录，便于事后复算访问范围。"""

    __tablename__ = "aiqe_secret_access_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    handle_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    consumer_node_key: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # ALLOW | DENY
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    requested_by_actor: Mapped[str] = mapped_column(String(120), nullable=False, default="worker")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_secret_access_audits_handle", "handle_id", "created_at"),
        Index("ix_aiqe_secret_access_audits_scope", "project_id", "run_id"),
    )
