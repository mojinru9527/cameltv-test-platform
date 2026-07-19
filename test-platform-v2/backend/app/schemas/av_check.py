"""AV check schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import math

from pydantic import BaseModel, ConfigDict, field_validator


AV_METRIC_TYPES = {
    "video_delay", "call_delay", "av_sync", "frame_rate", "first_frame",
}


class AvCheckTaskCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    stream_url: str = ""
    protocol: str = "HLS"        # HLS/FLV/WebRTC/DASH


class AvCheckTaskUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    stream_url: Optional[str] = None
    protocol: Optional[str] = None


class AvCheckMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    metric_name: str
    metric_value: float = 0.0
    threshold: float = 0.0
    pass_: bool = True
    detail: str = "{}"


class AvCheckMeasurementCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_type: str
    scenario: str = ""
    method: str = ""
    environment: str = ""
    device_info: str = ""
    network_condition: str = ""
    samples: list[float]
    threshold: float | None = None
    notes: str = ""

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, value: str) -> str:
        if value not in AV_METRIC_TYPES:
            raise ValueError("不支持的指标类型")
        return value

    @field_validator("samples")
    @classmethod
    def validate_samples(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("至少需要一个真实测量样本")
        if len(value) > 1000:
            raise ValueError("单次最多录入 1000 个样本")
        if any(not math.isfinite(float(item)) for item in value):
            raise ValueError("样本必须是有限数值")
        return [float(item) for item in value]

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("阈值必须是大于 0 的有限数值")
        return value


class AvCheckMeasurementUpdate(AvCheckMeasurementCreate):
    pass


class AvCheckMeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    metric_type: str
    metric_name: str
    scenario: str = ""
    method: str = ""
    environment: str = ""
    device_info: str = ""
    network_condition: str = ""
    samples: list[float]
    sample_count: int
    unit: str
    threshold: float
    comparator: str
    mean: float
    median: float
    min: float
    max: float
    stddev: float
    p95: float
    pass_basis: str
    passed: bool
    simulated: bool = False
    notes: str = ""
    creator_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AvCheckTaskBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: str = ""
    name: str
    protocol: str = "HLS"
    status: str = "idle"


class AvCheckTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    task_id: str = ""
    name: str
    stream_url: str = ""
    protocol: str = "HLS"
    status: str = "idle"
    last_result: str = "{}"
    creator_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_name: str = ""
    metrics: list[AvCheckMetricOut] = []
    measurements: list[AvCheckMeasurementOut] = []
