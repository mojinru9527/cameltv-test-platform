"""复用建议命中率（Batch 260 / B3-4）。

**不改既有契约**：`version_task_service.get_reuse_suggestions` 与
`GET /version-tasks/knowledge/reuse` 的返回保持原样（B12 与前端都依赖它）；
本服务只**旁挂**埋点与聚合。

命中率 = adopted / suggested。`suggested` 记"曾经带出过"，`adopted`/`rejected` 记人工决定；
同一 (task, suggestion_ref) 的同一 decision 只记一次（唯一约束），避免重复点击把分母撑大。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.reuse_suggestion import DECISIONS, ReuseSuggestionEvent


def record_suggestion(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    suggestion_ref: str,
    title: str = "",
) -> ReuseSuggestionEvent:
    return _record(
        db,
        project_id=project_id,
        task_id=task_id,
        suggestion_ref=suggestion_ref,
        title=title,
        decision="suggested",
        decided_by=0,
    )


def record_decision(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    suggestion_ref: str,
    decision: str,
    decided_by: int = 0,
) -> ReuseSuggestionEvent:
    if decision not in {"adopted", "rejected"}:
        raise APIException(
            code=400,
            msg=f"决定只能是 adopted 或 rejected，收到 {decision!r}",
            http_status=400,
        )
    # Batch 268 / C268-2：决策必须对应**真的被带出过**的建议。
    # 否则 adopted 可以凭空增加，命中率 = adopted/suggested 会 >1（本地实测出现过 2.5）。
    ref = (suggestion_ref or "").strip()
    suggested_id = db.scalar(
        select(ReuseSuggestionEvent.id).where(
            ReuseSuggestionEvent.project_id == project_id,
            ReuseSuggestionEvent.task_id == task_id,
            ReuseSuggestionEvent.suggestion_ref == ref,
            ReuseSuggestionEvent.decision == "suggested",
        )
    )
    if suggested_id is None:
        raise APIException(
            code=400,
            msg="该复用建议未被带出过，不能记录采纳/否掉（否则命中率分母失真）",
            http_status=400,
        )
    return _record(
        db,
        project_id=project_id,
        task_id=task_id,
        suggestion_ref=suggestion_ref,
        title="",
        decision=decision,
        decided_by=decided_by,
    )


def _record(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    suggestion_ref: str,
    title: str,
    decision: str,
    decided_by: int,
) -> ReuseSuggestionEvent:
    if decision not in DECISIONS:
        raise APIException(code=400, msg=f"未知埋点类型: {decision!r}", http_status=400)
    ref = (suggestion_ref or "").strip()
    if not ref:
        raise APIException(code=400, msg="suggestion_ref 不能为空", http_status=400)
    existing = db.scalar(
        select(ReuseSuggestionEvent).where(
            ReuseSuggestionEvent.task_id == task_id,
            ReuseSuggestionEvent.suggestion_ref == ref,
            ReuseSuggestionEvent.decision == decision,
        )
    )
    if existing is not None:
        # 幂等：重复点击不改变事实，也不撑大分母
        if title and not existing.title:
            existing.title = title
            db.commit()
            db.refresh(existing)
        return existing
    event = ReuseSuggestionEvent(
        project_id=project_id,
        task_id=task_id,
        suggestion_ref=ref,
        title=title,
        decision=decision,
        decided_by=decided_by,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def reuse_stats(db: Session, *, project_id: int) -> dict:
    """命中率统计（B3-4 DoD：命中率可统计；≥50% 目标进入 B4 验收）。

    Batch 268 / C268-2：只统计**有对应带出事件**的采纳/否掉，避免历史或不一致数据把
    `hit_rate` 抬到 1 以上（本地实测出现过 2.5 与 1.1875）。命中率因此天然有界于 [0, 1]。
    """
    rows = db.execute(
        select(
            ReuseSuggestionEvent.task_id,
            ReuseSuggestionEvent.suggestion_ref,
            ReuseSuggestionEvent.decision,
        ).where(ReuseSuggestionEvent.project_id == project_id)
    ).all()
    suggested_refs = {(task_id, ref) for task_id, ref, decision in rows if decision == "suggested"}
    adopted = sum(1 for task_id, ref, decision in rows if decision == "adopted" and (task_id, ref) in suggested_refs)
    rejected = sum(1 for task_id, ref, decision in rows if decision == "rejected" and (task_id, ref) in suggested_refs)
    suggested = len(suggested_refs)
    hit_rate = round(adopted / suggested, 4) if suggested else 0.0
    return {
        "suggested": suggested,
        "adopted": adopted,
        "rejected": rejected,
        "hit_rate": hit_rate,
        "meets_50pct": hit_rate >= 0.5 if suggested else None,
        "pending": max(0, suggested - adopted - rejected),
    }
