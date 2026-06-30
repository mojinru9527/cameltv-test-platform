"""UI test schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UiTestJobCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str = ""
    test_spec: str = ""
    browser: str = "chromium"       # chromium/firefox/webkit


class UiTestJobUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    description: Optional[str] = None
    test_spec: Optional[str] = None
    browser: Optional[str] = None


class UiTestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: str = "running"
    result: Optional[dict] = None
    screenshots: list[str] = []
    video_url: str = ""
    trace_id: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class UiTestJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    name: str
    description: str = ""
    test_spec: str = ""
    browser: str = "chromium"
    status: str = "idle"
    last_result: str = "{}"
    creator_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_name: str = ""
    last_run_status: str = ""
    last_run_time: Optional[datetime] = None


class UiTestJobDetailOut(UiTestJobOut):
    runs: list[UiTestRunOut] = []
