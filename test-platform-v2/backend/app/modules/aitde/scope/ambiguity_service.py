"""Ambiguity / Intent service (V30-042..V30-044, V30-047)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.intelligence.provider import (
    IntelligenceProvider,
    ScopeIntentContext,
)
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.scope import ambiguity_repository as repo
from app.modules.aitde.scope import service as scope_service
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityResolveRequest,
    IntentReviewRequest,
)
from app.modules.aitde.scope.models import Ambiguity, TestIntent


def _scope_items_context(db: Session, mission_id: int) -> list[dict]:
    rows, _ = scope_service.list_scope(db, mission_id)
    return [
        {
            "scope_key": r.scope_key,
            "name": r.name,
            "decision": r.decision,
            "risk_level": r.risk_level,
            "ai_confidence": r.ai_confidence,
            "reason": r.reason,
            "review_status": r.review_status,
            "source_refs": json.loads(r.source_refs_json or "[]"),
        }
        for r in rows
    ]


def analyze(
    db: Session,
    mission_id: int,
    project_id: int,
    user_id: int,
    provider: IntelligenceProvider | None = None,
) -> dict:
    mission_service.get_mission(db, mission_id, project_id)
    context = ScopeIntentContext(
        mission_id=mission_id, scope_items=_scope_items_context(db, mission_id)
    )
    from app.modules.aitde.intelligence.runner import run_intelligence

    operation_id = None
    if provider is not None:
        amb_output = provider.detect_ambiguities(context)
        intent_output = provider.design_intents(context)
        actor = provider.created_by_type
    else:
        (amb_output, intent_output), operation_id, actor = run_intelligence(
            db,
            project_id,
            mission_id,
            "ambiguity:intent:analyze",
            lambda prov: (prov.detect_ambiguities(context), prov.design_intents(context)),
        )

    ambiguities = repo.replace_ambiguities(
        db, mission_id, amb_output, actor=actor, user_id=user_id
    )
    intents = repo.replace_intents(
        db, mission_id, intent_output, actor=actor, user_id=user_id
    )
    db.commit()
    degraded = actor != "AI"
    fallback_used = degraded and operation_id is not None
    if fallback_used:
        reason = "AI 调用失败，已改用确定性规则，结果必须人工复核"
    elif degraded:
        reason = "未使用外部 AI，结果由确定性规则生成，必须人工复核"
    else:
        reason = None
    return {
        "ambiguity_count": len(ambiguities),
        "intent_count": len(intents),
        "generation": {
            "mode": actor,
            "degraded": degraded,
            "fallback_used": fallback_used,
            "confidence": 0.5 if degraded else 1.0,
            "reason": reason,
        },
    }


def list_ambiguities(db: Session, mission_id: int) -> list[Ambiguity]:
    return repo.list_ambiguities(db, mission_id)


def resolve_ambiguity(
    db: Session,
    ambiguity_id: int,
    project_id: int,
    user_id: int,
    req: AmbiguityResolveRequest,
) -> Ambiguity:
    ambiguity = db.get(Ambiguity, ambiguity_id)
    if not ambiguity:
        raise APIException(code=404, msg="歧义项不存在", http_status=404)
    mission_service.get_mission(db, ambiguity.mission_id, project_id)
    return repo.resolve_ambiguity(
        db,
        ambiguity,
        req.selected_option_key,
        req.resolution_note,
        req.status,
        user_id,
    )


def list_intents(db: Session, mission_id: int) -> list[TestIntent]:
    return repo.list_intents(db, mission_id)


def review_intent(
    db: Session,
    intent_id: int,
    project_id: int,
    user_id: int,
    req: IntentReviewRequest,
) -> TestIntent:
    intent = db.get(TestIntent, intent_id)
    if not intent:
        raise APIException(code=404, msg="意图项不存在", http_status=404)
    mission_service.get_mission(db, intent.mission_id, project_id)
    return repo.review_intent(
        db, intent, req.action == "approve", req.review_comment, user_id
    )


def blocking_policy(db: Session, mission_id: int) -> dict:
    """Contract-freeze precondition: no open P0/P1 ambiguity."""
    blocked = repo.has_open_p0p1(db, mission_id)
    return {
        "blocked": blocked,
        "reason": "存在未解决的 P0/P1 歧义" if blocked else None,
    }
