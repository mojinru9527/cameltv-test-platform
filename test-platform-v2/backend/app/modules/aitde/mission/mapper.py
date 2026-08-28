"""Mission model → dict mapper (V30-010/V30-011)."""
from __future__ import annotations

from typing import Any

from app.modules.aitde.mission.models import Mission


def mission_to_dict(row: Mission) -> dict[str, Any]:
    """Serialise a Mission row to the API-safe dictionary shape."""
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_key": row.mission_key,
        "mission_type": row.mission_type,
        "title": row.title,
        "version_label": row.version_label,
        "status": row.status,
        "owner_id": row.owner_id,
        "qa_owner_id": row.qa_owner_id,
        "default_environment_id": row.default_environment_id,
        "current_contract_version_id": row.current_contract_version_id,
        "acceptance_status": row.acceptance_status,
        "legacy_version_mission_id": row.legacy_version_mission_id,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "archived_at": row.archived_at.isoformat() if row.archived_at else None,
    }
