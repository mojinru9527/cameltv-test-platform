"""Defect schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DefectCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str = ""
    severity: str = "P2"            # P0/P1/P2/P3
    case_id: Optional[int] = None
    execution_id: Optional[int] = None
    assignee_id: int = 0
    external_id: str = ""
    external_url: str = ""


class DefectUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    case_id: Optional[int] = None
    execution_id: Optional[int] = None
    assignee_id: Optional[int] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    resolved_at: Optional[datetime] = None


class DefectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    defect_id: str = ""
    title: str
    description: str = ""
    severity: str = "P2"
    status: str = "open"
    case_id: Optional[int] = None
    execution_id: Optional[int] = None
    assignee_id: int = 0
    external_id: str = ""
    external_url: str = ""
    creator_id: int = 0
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # joined fields
    creator_name: str = ""
    case_title: str = ""
    assignee_name: str = ""
    # transitions (filled by detail endpoint)
    transitions: list[dict] = []


class DefectStats(BaseModel):
    total: int = 0
    by_severity: dict = {}
    by_status: dict = {}
