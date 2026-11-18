"""AUD-020：Platform Binding（AC/Case × 平台 × Driver/设备 × 能力状态）。

多条 AC/Case 可以复用同一业务意图，但 **Locator/操作/系统权限/设备状态/截图必须由各平台
Adapter 独立实现与独立验收**（v1.5 §03 AUD-020）。禁止把 Playwright viewport 模拟当成
iOS/Android 真机验收。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PlatformBinding(Base):
    __tablename__ = "aiqe_platform_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(8), nullable=False)  # AC | CASE
    target_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    platform_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    os_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    browser_or_app_version: Mapped[str] = mapped_column(
        String(80), nullable=False, default=""
    )
    device_model: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    driver_name: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    driver_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    #: 服务端根据 Capability Registry 计算的 6 态，客户端不得自报 VERIFIED。
    capability_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNAVAILABLE", index=True
    )
    test_profile: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "target_type",
            "target_id",
            "platform_id",
            name="uq_aiqe_platform_binding_target",
        ),
        Index("ix_aiqe_platform_bindings_project_platform", "project_id", "platform_id"),
    )
