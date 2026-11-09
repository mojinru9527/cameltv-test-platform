"""M1 / TA-006：Run Event Collector + Outbox（13 号 §4.11 / §18.6）。

事务规则：``append_event()`` 必须在**同一 DB 事务**内写 run_events + event_outbox，
可选的投影回调（更新 node_runs / step_attempts）也在同一事务内执行；本函数只 flush，
提交/回滚由调用方（API/Worker）决定。

幂等：``(run_id, producer_event_id)`` 已存在时直接返回既有事件，不重复入库。
序号：锁 TestRun 行后取 ``MAX(seq)+1``，保证单 Run 严格递增、无重复/跳号。
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.aiqe.models.event import EventOutbox, RunEvent
from app.aiqe.models.run import TestRun

PRODUCERS: frozenset[str] = frozenset(
    {"api_runner", "playwright", "keploy", "agent", "system", "node"}
)


class InvalidEventPayload(ValueError):
    """事件载荷/枚举不合法。"""


class RunNotFound(LookupError):
    """run_id 不存在。"""


def _validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise InvalidEventPayload("payload 必须是对象")
    version = payload.get("schema_version")
    if not isinstance(version, str) or not version:
        raise InvalidEventPayload("payload 必须包含非空 schema_version")


def append_event(
    db: Session,
    *,
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
    producer: str,
    producer_event_id: str | None = None,
    node_run_id: str | None = None,
    step_attempt_id: str | None = None,
    correlation_id: str | None = None,
    occurred_at: datetime | None = None,
    project: Callable[[Session, RunEvent], None] | None = None,
) -> tuple[RunEvent, bool]:
    """写入一条事件（+ outbox + 投影），返回 (event, created)。

    调用方负责 ``db.commit()`` / ``db.rollback()``；本函数不提交事务。
    """
    if not event_type:
        raise InvalidEventPayload("event_type 不能为空")
    if producer not in PRODUCERS:
        raise InvalidEventPayload(f"未知 producer: {producer!r}")
    _validate_payload(payload)

    # 行锁串行化同一 Run 的 seq 分配（SQLite 忽略 FOR UPDATE，单写者天然串行）
    run = db.scalar(select(TestRun).where(TestRun.id == run_id).with_for_update())
    if run is None:
        raise RunNotFound(run_id)

    if producer_event_id:
        existing = db.scalar(
            select(RunEvent).where(
                RunEvent.run_id == run_id,
                RunEvent.producer_event_id == producer_event_id,
            )
        )
        if existing is not None:
            return existing, False

    max_seq = db.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id))
    event = RunEvent(
        run_id=run_id,
        seq=int(max_seq or 0) + 1,
        node_run_id=node_run_id,
        step_attempt_id=step_attempt_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(UTC),
        producer=producer,
        correlation_id=correlation_id,
        payload_json=payload,
        producer_event_id=producer_event_id,
    )
    db.add(event)
    db.flush()

    db.add(EventOutbox(run_event_id=event.id))
    if project is not None:
        project(db, event)
    db.flush()
    return event, True


def list_events(
    db: Session, run_id: str, *, after_seq: int = 0, limit: int = 500
) -> list[RunEvent]:
    """按 seq 升序拉取事件（SSE 断线补拉）。"""
    limit = max(1, min(int(limit), 2000))
    return list(
        db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
            .order_by(RunEvent.seq.asc())
            .limit(limit)
        )
    )


def dispatch_outbox(db: Session, *, limit: int = 100) -> int:
    """标记待推送 outbox（dispatcher 调用）；返回本次标记数量。"""
    limit = max(1, min(int(limit), 1000))
    rows = list(
        db.scalars(
            select(EventOutbox)
            .where(EventOutbox.dispatched_at.is_(None))
            .order_by(EventOutbox.id.asc())
            .limit(limit)
        )
    )
    now = datetime.now(UTC)
    for row in rows:
        row.dispatched_at = now
        row.retry_count = int(row.retry_count or 0) + 1
    db.flush()
    return len(rows)


def mark_dispatch_failed(db: Session, outbox_id: int, error: str) -> None:
    row = db.get(EventOutbox, outbox_id)
    if row is None:
        return
    row.retry_count = int(row.retry_count or 0) + 1
    row.last_error = error[:2000]
    db.flush()
