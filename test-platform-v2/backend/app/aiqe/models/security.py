"""AUD-001：目标访问策略（Target Policy）持久化模型。

表 ``aiqe_target_policies``：项目级 / 环境级白名单与限额配置。

约束（13 号 §7、v1.5 AUD-001）：
- 策略只由服务端（管理员）写入，Workflow / Agent 只能提供业务目标 URL，不能覆盖
  白名单、私网策略、代理、TLS 校验和 redirect 策略；
- 每条策略带 ``version``，安全拒绝与被审计请求必须记录命中的版本。
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TargetPolicyRecord(Base):
    __tablename__ = "aiqe_target_policies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL = 项目级默认策略；非 NULL = 仅对该环境生效（优先于项目级）
    environment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("environment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "environment_id",
            "name",
            "version",
            name="uq_aiqe_target_policies_scope_version",
        ),
        Index("ix_aiqe_target_policies_project_active", "project_id", "active"),
    )
