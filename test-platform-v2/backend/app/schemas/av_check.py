"""AV check schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
