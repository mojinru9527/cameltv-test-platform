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
    query_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current_project"
    )
    #: 服务端连接引用（如 `aiqe_test_readonly`），**不是**可被 Workflow 传入的 URL。
    connection_ref: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_params: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
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
