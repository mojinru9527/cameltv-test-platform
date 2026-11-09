"""M1 / TA-006：Run 事件与 Outbox 模型（13 号 §4.11）。

- run_events：append-only；`(run_id, seq)` 唯一、`(run_id, producer_event_id)` 幂等；
- event_outbox：同一事务写入，供 SSE/Redis dispatcher 推送。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    node_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_runs.id", ondelete="SET NULL"), nullable=True
    )
    step_attempt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("step_attempts.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    producer: Mapped[str] = mapped_column(String(80), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    producer_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    outbox: Mapped[EventOutbox | None] = relationship(
        back_populates="event", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),
        UniqueConstraint("run_id", "producer_event_id", name="uq_run_events_run_producer_event"),
        Index("ix_run_events_run_seq", "run_id", "seq"),
    )


class EventOutbox(Base):
    __tablename__ = "event_outbox"

    # PostgreSQL BIGINT；SQLite 需 INTEGER 才能走 rowid 自增
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    run_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("run_events.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[RunEvent] = relationship(back_populates="outbox")
