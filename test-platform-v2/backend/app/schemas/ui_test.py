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
    environment_id: int | None = None


class UiTestJobUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    description: Optional[str] = None
    test_spec: Optional[str] = None
    browser: Optional[str] = None
    environment_id: int | None = None


class UiTestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: str = "pending"
    result: Optional[dict] = None
    screenshots: list[str] = []
    video_url: str = ""
    trace_id: str = ""
    base_url: str = ""
    browser: str = ""
    duration: Optional[float] = None
    artifact_dir: str = ""
    report_json_path: str = ""
    html_report_path: str = ""
    error_message: str = ""
    stdout: str = ""
    stderr: str = ""
    process_id: int | None = None
    cancel_requested: bool = False
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
    environment_id: int | None = None
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


# ── UiTestScript ──

class UiTestScriptCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    script_key: str = ""
    spec_path: str = ""
    module: str = ""
    owner: str = ""
    tags: str = "[]"
    status: str = "active"


class UiTestScriptUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    script_key: Optional[str] = None
    spec_path: Optional[str] = None
    module: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None


class UiTestScriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    name: str
    script_key: str
    spec_path: str
    module: str
    owner: str
    tags: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
