"""Pydantic schemas for performance monitoring API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Device ──

class PerfDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    device_name: str
    device_model: str
    platform: str
    os_version: str
    status: str
    installed_apps: list[str] | None = None


class DeviceListResponse(BaseModel):
    devices: list[PerfDeviceOut]


# ── Session ──

class PerfSessionCreate(BaseModel):
    device_id: str
    platform: str = "Android"
    pkg_name: str
    device_name: str = ""
    device_model: str = ""
    metrics: list[str] = Field(default_factory=lambda: ["cpu", "memory", "fps", "jank"])
    duration: int = 300  # seconds, 0 = unlimited


class PerfSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    device_id: str
    device_name: str
    device_model: str
    platform: str
    pkg_name: str
    metrics: str
    status: str
    duration: int
    actual_duration_s: int
    summary_json: str
    error_message: str
    creator_id: int
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class PerfSessionListResponse(BaseModel):
    items: list[PerfSessionOut]
    total: int
    page: int
    page_size: int


# ── Metric Stats ──

class MetricStats(BaseModel):
    metric_type: str
    unit: str
    samples: int
    mean: float
    median: float
    p95: float
    min_val: float
    max_val: float
    stddev: float
    threshold: float
    threshold_comparator: str   # ">=" or "<="
    passed: bool


class AnomalyEvent(BaseModel):
    timestamp: float
    event_type: str            # jank / anr / crash / fps_drop / cpu_spike / memory_spike
    detail: str
    metric_snapshot: dict | None = None


# ── Metric Data Point ──

class MetricDataPoint(BaseModel):
    timestamp: float
    elapsed_s: float
    values: dict  # {"cpu": {...}, "memory": {...}, "fps": {...}, ...}


class MetricTimeseriesResponse(BaseModel):
    session_id: str
    metrics: list[MetricDataPoint]
    total_points: int


# ── Report ──

class PerfReportResponse(BaseModel):
    session: PerfSessionOut
    metrics: list[MetricStats]
    anomalies: list[AnomalyEvent]


# ── Compare ──

class CompareRequest(BaseModel):
    session_a_id: int
    session_b_id: int


class MetricDelta(BaseModel):
    metric_type: str
    session_a_mean: float
    session_b_mean: float
    delta_absolute: float
    delta_percent: float
    direction: str          # "improved" | "degraded" | "unchanged"
    significant: bool       # |delta_percent| > 10%


class CompareResponse(BaseModel):
    session_a: PerfSessionOut
    session_b: PerfSessionOut
    deltas: list[MetricDelta]
