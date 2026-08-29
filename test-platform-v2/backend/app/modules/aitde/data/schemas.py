"""AITDE V3.2 DataSource schemas (V32-001)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import DataSourceAccessMode, DataSourceType


class DataSourceCreate(BaseModel):
    source_type: DataSourceType
    name: str = Field(..., max_length=255)
    environment_id: int | None = None
    network_zone: str = Field(default="", max_length=64)
    secret_ref: str | None = Field(default=None, max_length=255)
    access_mode: DataSourceAccessMode = DataSourceAccessMode.READONLY
    # Connection metadata (host/database/table set etc). Never stores secrets.
    config: dict[str, Any] | None = None
    policy_ref: str | None = Field(default=None, max_length=255)


class DataSourceRead(BaseModel):
    id: int
    project_id: int
    environment_id: int | None = None
    source_type: str
    name: str
    network_zone: str
    # A reference to the secret, never the secret value it points at.
    secret_ref: str | None = None
    access_mode: str
    config_json: str
    policy_ref: str | None = None
    status: str
    created_by: int
    created_at: str | None = None
    updated_at: str | None = None
