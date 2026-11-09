"""M1 / TA-008：Run Console 只读 API schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_key: str
    source_type: str
    status: str
    outcome: str | None = None
    build_ref: str = ""
    commit_sha: str = ""
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None


class RunEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    seq: int
    event_type: str
    producer: str
    occurred_at: datetime
    payload_json: dict[str, Any] = {}
    node_run_id: str | None = None
    step_attempt_id: str | None = None


class RunArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    artifact_type: str
    sha256: str
    size_bytes: int
    mime_type: str
    redaction_status: str
    created_at: datetime
