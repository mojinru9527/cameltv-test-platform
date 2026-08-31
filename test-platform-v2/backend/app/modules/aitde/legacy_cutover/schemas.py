"""AITDE V4.0 Legacy Cutover API schemas (V40)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UsageRecordIn(BaseModel):
    """Record/upsert a legacy v1 surface usage observation (V40-001)."""

    consumer_type: str = Field(default="UNKNOWN", max_length=16)
    surface_kind: str = Field(default="ENDPOINT", max_length=16)
    path: str = Field(default="", max_length=255)
    method: str = Field(default="", max_length=16)
    object_type: str = Field(default="TEST_CASE", max_length=32)
    object_id: int | None = None
    owner: str = Field(default="", max_length=64)
    traffic_count: int = Field(default=1, ge=0)
    replacement_v2: str = Field(default="", max_length=255)
    deprecation_stage: str = Field(default="ACTIVE", max_length=16)
    sunset_date: str | None = Field(default=None, max_length=32)
    rollback_switch: str = Field(default="", max_length=64)


class UsageRecordOut(BaseModel):
    id: int
    consumer_type: str
    surface_kind: str
    path: str
    method: str
    object_type: str
    object_id: int | None
    owner: str
    traffic_count: int
    replacement_v2: str
    deprecation_stage: str
    sunset_date: str | None
    rollback_switch: str
    last_seen_at: datetime


class MappingUpsertIn(BaseModel):
    """Create or refresh a legacy -> canonical object mapping (V40-002)."""

    legacy_type: str = Field(..., max_length=32)
    legacy_id: int
    canonical_type: str = Field(..., max_length=32)
    canonical_id: int
    # 042: fail-closed — optional status override must be an allowed value.
    migration_status: str | None = Field(default=None, max_length=16)


class MappingOut(BaseModel):
    id: int
    legacy_type: str
    legacy_id: int
    canonical_type: str
    canonical_id: int
    migration_status: str
    verified_at: datetime | None


class CutoverBatchIn(BaseModel):
    """Define a cutover batch by selector (V40-002)."""

    batch_key: str = Field(..., max_length=64)
    object_type: str = Field(..., max_length=32)
    criteria: dict = Field(default_factory=dict)
    project_id: int = Field(default=0)


class CutoverBatchOut(BaseModel):
    id: int
    batch_key: str
    object_type: str
    status: str
    planned_count: int
    migrated_count: int
    failed_count: int
    started_at: datetime | None
    finished_at: datetime | None
