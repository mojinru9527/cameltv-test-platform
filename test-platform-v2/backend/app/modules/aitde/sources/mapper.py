"""Source model → dict mappers (V30-025)."""
from __future__ import annotations

from typing import Any

from app.modules.aitde.sources.models import SourceArtifact, SourceFragment


def fragment_to_dict(row: SourceFragment) -> dict[str, Any]:
    return {
        "id": row.id,
        "artifact_id": row.artifact_id,
        "fragment_key": row.fragment_key,
        "title": row.title,
        "text": row.text,
        "location_json": row.location_json,
        "content_hash": row.content_hash,
        "sequence": row.sequence,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def artifact_to_dict(row: SourceArtifact | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "project_id": row.project_id,
        "source_type": row.source_type,
        "provider": row.provider,
        "name": row.name,
        "uri": row.uri,
        "content_hash": row.content_hash,
        "version_label": row.version_label,
        "sensitivity": row.sensitivity,
        "parse_status": row.parse_status,
        "metadata_json": row.metadata_json,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "fragment_count": int(getattr(row, "_fragment_count", 0) or 0),
    }
