"""AUD-002：DB Query Registry（登记式只读查询模板）。

Workflow 只能引用 ``query_key``，SQL、连接、表范围与限额全部由服务端登记（v1.5 §01 AUD-002）。
``project_id`` 必须出现在语句里，由执行器服务端注入，**不信任客户端/模型输入**。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RegisteredQuery(Base):
    __tablename__ = "aiqe_registered_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: V16-004：登记可绑定 Environment；NULL 表示项目级默认查询。
    #: 不使用 FK：SQLite 无法 DROP 带 FK 的列（迁移必须可回滚），归属校验在服务端完成。
    environment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    query_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current_project"
    )
    #: 服务端连接引用（如 `aiqe_test_readonly`），**不是**可被 Workflow 传入的 URL。
    connection_ref: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    statement_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    allowed_params: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    #: V16-004：表/列白名单（服务端登记，执行时强制）。
    allowed_tables: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    #: pending | approved | disabled
    approval_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="approved"
    )
    max_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_execution_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    result_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "query_key", "version", name="uq_aiqe_registered_queries_key_version"
        ),
        Index("ix_aiqe_registered_queries_project_key", "project_id", "query_key"),
    )


class QueryExecutionAudit(Base):
    """V16-004 §8：每次登记查询执行的服务端审计（不含明文参数）。"""

    __tablename__ = "aiqe_query_execution_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    environment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    query_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    query_key: Mapped[str] = mapped_column(String(80), nullable=False)
    query_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    params_redacted_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executor_identity: Mapped[str] = mapped_column(String(120), nullable=False, default="worker")
    policy_decision: Mapped[str] = mapped_column(String(16), nullable=False, default="ALLOW")
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_query_execution_audits_scope", "project_id", "query_key", "created_at"),
    )