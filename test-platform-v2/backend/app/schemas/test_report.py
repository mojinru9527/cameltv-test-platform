"""Report schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    plan_id: int
    name: str
    description: str = ""


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    report_id: str = ""
    name: str = ""
    description: str = ""
    plan_id: int = 0
    creator_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # filled by service:
    plan_name: str = ""


class ReportDetailOut(ReportOut):
    content: Optional[dict] = None


class TrendPoint(BaseModel):
    """A single data point on a trend chart."""
    date: str = ""                      # ISO date string
    report_id: int = 0
    report_name: str = ""
    pass_rate: float = 0.0              # percentage (0-100)
    total: int = 0
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    block_count: int = 0
    open_p0: int = 0
    open_p1: int = 0
    open_p2: int = 0
    open_total: int = 0


class TrendOut(BaseModel):
    """Multi-plan trend + defect convergence data."""
    points: list[TrendPoint] = []
    summary: dict = {}
