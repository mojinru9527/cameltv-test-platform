"""Ambiguity / Intent model → dict mappers (V30-045/V30-046)."""
from __future__ import annotations

from typing import Any

from app.modules.aitde.scope.models import Ambiguity, TestIntent


def ambiguity_to_dict(row: Ambiguity) -> dict[str, Any]:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "ambiguity_key": row.ambiguity_key,
        "title": row.title,
        "description": row.description,
        "severity": row.severity,
        "status": row.status,
        "candidate_options_json": row.candidate_options_json,
        "selected_option_json": row.selected_option_json,
        "ai_confidence": row.ai_confidence,
        "resolution_note": row.resolution_note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def intent_to_dict(row: TestIntent) -> dict[str, Any]:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "intent_key": row.intent_key,
        "title": row.title,
        "business_goal": row.business_goal,
        "risk_level": row.risk_level,
        "review_status": row.review_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
