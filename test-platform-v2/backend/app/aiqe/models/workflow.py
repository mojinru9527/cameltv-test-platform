"""M2 / TA-010：Workflow 定义 + 资源锁模型。

- workflow_definitions（13 号 §4.6）：approved 后 graph_json/checksum 冻结；
- resource_locks（§6.4）：key 级锁 + TTL + fencing token（单调递增）。
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
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("test_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("scenario_id", "version", name="uq_workflow_scenario_version"),
    )


class ResourceLock(Base):
    """资源锁行；release 只把 expires_at 置为过期，保留 fencing token 单调性。"""

    __tablename__ = "resource_locks"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    fencing_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
