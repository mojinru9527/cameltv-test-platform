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
