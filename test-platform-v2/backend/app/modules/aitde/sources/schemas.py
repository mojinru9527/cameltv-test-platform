"""Source Pydantic schemas (V30-025)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import SourceRole, SourceType


class SourceArtifactCreate(BaseModel):
    source_type: SourceType
    provider: str = ""
    # Requirement: reference an existing requirement document
    requirement_doc_id: int | None = None
    # OpenAPI: a URL / spec reference
    uri: str | None = None
    # Manual note: name + content
    name: str | None = Field(default=None, max_length=255)
    content: str | None = None
    role: SourceRole = SourceRole.REQUIREMENT


class SourceParseRequest(BaseModel):
    pass


class SourceArtifactRead(BaseModel):
    id: int
    project_id: int
    source_type: str
    provider: str
    name: str
    uri: str
    content_hash: str
    version_label: str
    sensitivity: str
    parse_status: str
    metadata_json: str
    created_by: int
    created_at: str | None = None
    updated_at: str | None = None
    role: str | None = None
    fragment_count: int = 0


class SourceFragmentRead(BaseModel):
    id: int
    artifact_id: int
    fragment_key: str
    title: str
    text: str
    location_json: str
    content_hash: str
    sequence: int
    created_at: str | None = None


class SourceParseResult(BaseModel):
    artifact_id: int
    parse_status: str
    fragment_count: int
    operation_id: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
