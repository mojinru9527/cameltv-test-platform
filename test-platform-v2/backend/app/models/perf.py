"""Performance monitoring ORM models — PerfSession + PerfMetric + PerfDevice."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PerfSession(Base):
    """一次性能采集会话。"""

    __tablename__ = "perf_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    session_id: Mapped[str] = mapped_column(String(50), default="", index=True)  # PERF-YYYYMMDD-NNN
    device_id: Mapped[str] = mapped_column(String(200), default="")              # ADB serial / iOS UDID
    device_name: Mapped[str] = mapped_column(String(200), default="")
    device_model: Mapped[str] = mapped_column(String(100), default="")
    platform: Mapped[str] = mapped_column(String(20), default="Android")        # Android / iOS
    pkg_name: Mapped[str] = mapped_column(String(200), default="")
    metrics: Mapped[str] = mapped_column(String(200), default="")               # comma-separated: cpu,memory,fps,jank,startup,anr
    status: Mapped[str] = mapped_column(String(20), default="pending")           # pending/running/completed/failed/cancelled
    duration: Mapped[int] = mapped_column(default=300)                           # planned duration in seconds
    actual_duration_s: Mapped[int] = mapped_column(default=0)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")               # JSON summary stats
    error_message: Mapped[str] = mapped_column(Text, default="")
    creator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    ended_at: Mapped[datetime | None] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    samples: Mapped[list["PerfMetric"]] = relationship(
        "PerfMetric", back_populates="session",
        cascade="all, delete-orphan", order_by="PerfMetric.id",
    )


class PerfMetric(Base):
    """时序性能指标数据点。每个采样周期一条记录，存储全量指标快照 JSON。"""

    __tablename__ = "perf_metric"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("perf_session.id"), index=True)
    timestamp: Mapped[float] = mapped_column(default=0.0, index=True)             # epoch seconds
    elapsed_s: Mapped[float] = mapped_column(default=0.0)                         # seconds since session start
    metric_type: Mapped[str] = mapped_column(String(20), default="snapshot")      # "snapshot" for full snapshot, or specific metric
    data_json: Mapped[str] = mapped_column(Text, default="{}")                    # {"cpu": {...}, "memory": {...}, "fps": {...}, ...}

    session: Mapped["PerfSession"] = relationship("PerfSession", back_populates="samples")


class PerfDevice(Base):
    """已连接的测试设备信息缓存。"""

    __tablename__ = "perf_device"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)  # ADB serial / iOS UDID
    device_name: Mapped[str] = mapped_column(String(200), default="")
    device_model: Mapped[str] = mapped_column(String(100), default="")
    platform: Mapped[str] = mapped_column(String(20), default="Android")
    os_version: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="online")             # online / offline
    last_seen_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
