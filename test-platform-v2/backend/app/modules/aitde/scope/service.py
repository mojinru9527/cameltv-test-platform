"""Scope service (V30-035/V30-036/V30-039).

Runs context → AI → validation → persist → audit for scope analysis, then
supports bulk review (approve/reject) and a completion policy.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import ParseStatus, ReviewStatus, ScopeDecision
from app.modules.aitde.intelligence.provider import IntelligenceProvider
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.scope import repository
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.scope.schemas import (
    ScopeAnalysisOutput,
    ScopeBulkReviewRequest,
    ScopeSummary,
)
from app.modules.aitde.sources import service as source_service


def _context_from_parsed_sources(db: Session, mission_id: int, project_id: int):
    artifacts = source_service.list_sources(db, mission_id)
    parsed = [a for a in artifacts if a.parse_status == ParseStatus.PARSED.value]
    if not parsed:
        raise APIException(
            code=400, msg="Scope 分析需要至少一个已解析的 Source", http_status=400
        )
    fragments: list[tuple[int, int, str, str]] = []
    for artifact in parsed:
        for frag in source_service.fragments(db, artifact.id, project_id):
            fragments.append((artifact.id, frag.id, frag.title, frag.text))
    return fragments


def analyze_scope(
    db: Session,
    mission_id: int,
    project_id: int,
    user_id: int,
    provider: IntelligenceProvider | None = None,
) -> list[ScopeItem]:
    mission_service.get_mission(db, mission_id, project_id)
    fragments = _context_from_parsed_sources(db, mission_id, project_id)

    from app.modules.aitde.intelligence.provider import ScopeContext
    from app.modules.aitde.intelligence.runner import run_intelligence

    context = ScopeContext(mission_id=mission_id, fragments=fragments)
    if provider is not None:
        output: ScopeAnalysisOutput = provider.analyze_scope(context)
        actor = provider.created_by_type
    else:
        output, _op_id, actor = run_intelligence(
            db,
            project_id,
            mission_id,
            "scope:analyze",
            lambda prov: prov.analyze_scope(context),
        )

    # Validation already enforced by ScopeAnalysisOutput's strict schemas.
    items = repository.replace_items(db, mission_id, output, actor=actor, user_id=user_id)
    db.commit()
    db.refresh(items[0]) if items else None
    _audit(db, project_id, user_id, mission_id, "scope:analyze", f"{len(items)} items")
    return items


def list_scope(db: Session, mission_id: int) -> tuple[list[ScopeItem], ScopeSummary]:
    rows = repository.list_items(db, mission_id)
    result = repository.summary(db, mission_id)
    return rows, result


def get_scope_item(db: Session, scope_id: int, mission_id: int) -> ScopeItem:
    row = repository.get_item(db, scope_id, mission_id)
    if not row:
        raise APIException(code=404, msg="Scope 项不存在", http_status=404)
    return row


def review_scope(
    db: Session,
    mission_id: int,
    project_id: int,
    user_id: int,
    req: ScopeBulkReviewRequest,
) -> ScopeSummary:
    mission_service.get_mission(db, mission_id, project_id)
    for item in req.items:
        target = _get_by_scope_key(db, item.scope_key, mission_id)
        if not target:
            continue
        approved = item.action == "approve"
        target.review_status = (
            ReviewStatus.APPROVED.value if approved else ReviewStatus.REJECTED.value
        )
        target.decision = (
            item.decision.value if approved else ScopeDecision.EXCLUDE.value
        )
        if item.reason:
            target.reason = item.reason
        target.reviewed_by = user_id
        target.reviewed_at = datetime.now()
    db.commit()
    _audit(
        db, project_id, user_id, mission_id, "scope:review", f"{len(req.items)} items"
    )
    return repository.summary(db, mission_id)


def _get_by_scope_key(db: Session, scope_key: str, mission_id: int) -> ScopeItem | None:
    from sqlalchemy import select

    from app.modules.aitde.scope.models import ScopeItem

    return db.scalar(
        select(ScopeItem).where(
            ScopeItem.mission_id == mission_id, ScopeItem.scope_key == scope_key
        )
    )


def complete_policy(db: Session, mission_id: int) -> ScopeSummary:
    result = repository.summary(db, mission_id)
    if result.total == 0:
        raise APIException(code=400, msg="Scope 尚未生成", http_status=400)
    return result


def _audit(
    db: Session,
    project_id: int,
    user_id: int,
    mission_id: int,
    action: str,
    detail: str,
) -> None:
    try:
        from app.models.user import User
        from app.services.audit_service import write_audit

        # 审计日志统一记录稳定的登录名，避免昵称与其他审计来源口径不一致。
        user = db.get(User, user_id) if user_id else None
        username = user.username if user else ""

        write_audit(
            db,
            user_id=user_id,
            username=username,
            project_id=project_id,
            action=action,
            target=f"mission:{mission_id}",
            detail=detail,
        )
    except Exception:  # noqa: BLE001
        pass
