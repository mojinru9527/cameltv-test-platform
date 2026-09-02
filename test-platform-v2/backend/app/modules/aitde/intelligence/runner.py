"""Batch 207 — intelligence runner with honest degradation + ai_ops audit.

``run_intelligence`` builds the provider (AI when configured, else
deterministic) and runs a callable. Real AI calls are recorded in
``ai_operations``; when a configured model is unreachable or returns an
unusable shape the operation is marked FAILED and the call is re-run on the
deterministic baseline so the review flow stays usable — but the persisted
provenance (``created_by_type``) is DETERMINISTIC, never a fake AI claim.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


def run_intelligence(
    db: Session,
    project_id: int,
    mission_id: int,
    operation_type: str,
    fn: Callable[[Any], T],
    *args: Any,
    **kwargs: Any,
) -> tuple[T, int | None, str]:
    """Run ``fn(provider, *args, **kwargs)`` and return (result, op_id, actor).

    ``actor`` is "AI" when a real model produced the result and
    "DETERMINISTIC" when the baseline did (including after a failed AI call).
    """
    from app.modules.aitde.intelligence.llm_sync import (
        IntelligenceLLMError,
        IntelligenceLLMResponseError,
    )
    from app.modules.aitde.intelligence.provider import (
        DeterministicScopeProvider,
        build_intelligence_provider,
    )

    prov = build_intelligence_provider(db, project_id)
    if prov.mode != "ai":
        return fn(prov, *args, **kwargs), None, prov.created_by_type

    from app.modules.aitde.ai_ops import service as ai_ops_service

    op = ai_ops_service.create_operation(
        db, project_id=project_id, mission_id=mission_id,
        operation_type=operation_type,
    )
    ai_ops_service.mark_running(db, op)
    try:
        result = fn(prov, *args, **kwargs)
    except (IntelligenceLLMError, IntelligenceLLMResponseError) as exc:
        ai_ops_service.mark_failed(
            db, op, code="AI_CALL_FAILED", message=str(exc)[:500]
        )
        fallback = DeterministicScopeProvider()
        return fn(fallback, *args, **kwargs), op.id, fallback.created_by_type
    ai_ops_service.mark_succeeded(db, op, result_ref={})
    return result, op.id, prov.created_by_type


def latest_operation_id(
    db: Session,
    mission_id: int,
    project_id: int,
    operation_type: str | None = None,
) -> int | None:
    """Return the newest AI operation id for a mission (or None).

    Deterministic flows never write operations, so this returns None and the
    API keeps ``operation_id=None`` for them (honest: no AI happened).
    """
    from app.modules.aitde.ai_ops import service as ai_ops_service

    rows = ai_ops_service.list_operations(db, mission_id, project_id=project_id)
    if not rows:
        return None
    if operation_type is None:
        return rows[0].id
    for row in rows:
        if row.operation_type == operation_type:
            return row.id
    return None
