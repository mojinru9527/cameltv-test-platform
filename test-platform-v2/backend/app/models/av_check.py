"""AV check ORM models — AvCheckTask + AvCheckMetric."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AvCheckTask(Base):
    __tablename__ = "av_check_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    task_id: Mapped[str] = mapped_column(String(50), default="")        # AV-YYYYMMDD-NNN
    name: Mapped[str] = mapped_column(String(200), default="")
    stream_url: Mapped[str] = mapped_column(String(500), default="")
    protocol: Mapped[str] = mapped_column(String(20), default="HLS")    # HLS/FLV/WebRTC/DASH
    status: Mapped[str] = mapped_column(String(20), default="idle")     # idle/running/done/fail
    last_result: Mapped[str] = mapped_column(Text, default="{}")        # JSON summary
    creator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    metrics: Mapped[list["AvCheckMetric"]] = relationship(
        "AvCheckMetric", back_populates="task",
        cascade="all, delete-orphan", order_by="AvCheckMetric.id",
    )


class AvCheckMetric(Base):
    __tablename__ = "av_check_metric"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("av_check_task.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(50))        # 起播时延/卡顿率/音画同步/首帧时间/缓冲次数
    metric_value: Mapped[float] = mapped_column(default=0.0)
    threshold: Mapped[float] = mapped_column(default=0.0)
    pass_: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str] = mapped_column(Text, default="{}")     # JSON extra info

    task: Mapped["AvCheckTask"] = relationship("AvCheckTask", back_populates="metrics")
