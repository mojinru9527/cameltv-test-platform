"""Scope model → dict mapper (V30-037)."""
from __future__ import annotations

from typing import Any

from app.modules.aitde.scope.models import ScopeItem


def scope_item_to_dict(row: ScopeItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "scope_key": row.scope_key,
        "scope_type": row.scope_type,
        "name": row.name,
        "decision": row.decision,
        "test_depth": row.test_depth,
        "risk_level": row.risk_level,
        "reason": row.reason,
        "ai_confidence": row.ai_confidence,
        "review_status": row.review_status,
        "created_by_type": row.created_by_type,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
