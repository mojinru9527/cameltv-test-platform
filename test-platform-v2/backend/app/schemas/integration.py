"""Integration config schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class IntegrationConfigCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    provider_type: Literal["jira", "tapd"] = "jira"
    base_url: str = ""
    auth_json: str = ""  # plaintext on input → encrypted before storage
    field_mapping: str = "{}"  # JSON string
    sync_direction: str = "bidirectional"  # bidirectional | push_only | pull_only
    sync_interval_minutes: int = 0
    enabled: bool = True


class IntegrationConfigUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    auth_json: Optional[str] = None
    field_mapping: Optional[str] = None
    sync_direction: Optional[str] = None
    sync_interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


class IntegrationConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    name: str = ""
    provider_type: str = "jira"
    base_url: str = ""
    auth_json: str = "********"  # always masked in output
    field_mapping: str = "{}"
    sync_direction: str = "bidirectional"
    sync_interval_minutes: int = 0
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TestConnectionRequest(BaseModel):
    provider_type: str  # "jira" | "tapd"
    base_url: str
    auth_json: str  # plaintext for test


class TestConnectionResponse(BaseModel):
    success: bool
    message: str = ""


class SyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    integration_id: int = 0
    defect_id: int = 0
    direction: str = "push"
    status: str = "success"
    external_id: str = ""
    message: str = ""
    created_at: Optional[datetime] = None
