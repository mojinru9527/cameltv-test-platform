"""QualityGateConfig — 项目级质量门禁配置。

Dimensions (all optional; 0 means "skip this check"):
  pass_rate_threshold   — minimum pass rate % (0–100)
  p0_max / p1_max       — max allowed open P0/P1 defects
  coverage_threshold    — minimum requirement coverage % (0–100, 0=off)
  max_failed_cases      — max allowed failed cases (0=unlimited)
  max_blocked_cases     — max allowed blocked cases (0=unlimited)
"""
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
    # R3 extension: additional gate dimensions (all default 0 = disabled)
    coverage_threshold: Mapped[int] = mapped_column(Integer, default=0)   # 0-100, 0=off
    max_failed_cases: Mapped[int] = mapped_column(Integer, default=0)     # 0=unlimited
    max_blocked_cases: Mapped[int] = mapped_column(Integer, default=0)    # 0=unlimited
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
