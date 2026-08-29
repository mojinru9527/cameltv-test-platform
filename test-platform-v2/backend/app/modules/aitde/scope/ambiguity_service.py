"""Ambiguity / Intent service (V30-042..V30-044, V30-047)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.intelligence.provider import (
    IntelligenceProvider,
    LegacyAIServiceProvider,
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
    prov = provider or LegacyAIServiceProvider()
    amb_output = prov.detect_ambiguities(context)
    intent_output = prov.design_intents(context)

    ambiguities = repo.replace_ambiguities(
        db, mission_id, amb_output, actor="AI", user_id=user_id
    )
    intents = repo.replace_intents(
        db, mission_id, intent_output, actor="AI", user_id=user_id
    )
    db.commit()
    return {
        "ambiguity_count": len(ambiguities),
        "intent_count": len(intents),
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
