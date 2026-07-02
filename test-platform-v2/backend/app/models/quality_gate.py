"""QualityGateConfig — 项目级质量门禁配置。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class QualityGateConfig(Base):
    __tablename__ = "quality_gate_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, unique=True, index=True)
    pass_rate_threshold: Mapped[int] = mapped_column(default=80)  # 0-100
    p0_max: Mapped[int] = mapped_column(default=0)                # max allowed open P0 defects
    p1_max: Mapped[int] = mapped_column(default=5)                # max allowed open P1 defects
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
