"""V16-006：Outbox 写入与 relay（幂等、可重试）。"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.aiqe.models.outbox import FAILED, MAX_ATTEMPTS, PENDING, PUBLISHED, AIQEOutbox

Publisher = Callable[[AIQEOutbox], None]


def enqueue(
    db: Session,
    *,
    project_id: int,
    event_type: str,
    payload: Mapping[str, Any],
    producer_event_id: str,
    run_id: str | None = None,
) -> AIQEOutbox:
    """同事务写入（幂等：同一 producer_event_id 只存在一条）。"""
    existing = db.scalar(
        select(AIQEOutbox).where(AIQEOutbox.producer_event_id == str(producer_event_id))
    )
    if existing is not None:
        return existing
    row = AIQEOutbox(
        project_id=int(project_id),
        run_id=str(run_id) if run_id else None,
        event_type=str(event_type)[:64],
        payload_json=dict(payload),
        producer_event_id=str(producer_event_id)[:160],
        status=PENDING,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_row = db.scalar(
            select(AIQEOutbox).where(AIQEOutbox.producer_event_id == str(producer_event_id))
        )
        if existing_row is None:
            raise
        row = existing_row
    return row


def relay(
    db: Session,
    *,
    publisher: Publisher | None = None,
    limit: int = 100,
    now: datetime | None = None,
) -> dict[str, int]:
    """发布 pending 事件；publisher 为空时仅标记 published（本地 Job 已持久化）。"""
    moment = now or datetime.now(UTC)
    rows = list(
        db.scalars(
            select(AIQEOutbox)
            .where(AIQEOutbox.status == PENDING, AIQEOutbox.available_at <= moment)
            .order_by(AIQEOutbox.created_at)
            .limit(max(1, int(limit)))
        )
    )
    published = 0
    failed = 0
    for row in rows:
        try:
            if publisher is not None:
                publisher(row)
            row.status = PUBLISHED
            row.published_at = moment
            row.last_error = ""
            published += 1
        except Exception as exc:
            row.attempts = int(row.attempts or 0) + 1
            row.last_error = f"{type(exc).__name__}: {exc}"[:500]
            row.available_at = moment + timedelta(seconds=min(300, 2 ** row.attempts))
            if row.attempts >= MAX_ATTEMPTS:
                row.status = FAILED
            failed += 1
    db.flush()
    return {"scanned": len(rows), "published": published, "failed": failed}


def pending_count(db: Session) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.count()).select_from(AIQEOutbox).where(AIQEOutbox.status == PENDING)
        )
        or 0
    )


__all__ = ["MAX_ATTEMPTS", "PENDING", "PUBLISHED", "enqueue", "pending_count", "relay"]
