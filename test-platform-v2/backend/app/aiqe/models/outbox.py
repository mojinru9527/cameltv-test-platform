"""V16-006：AIQE Outbox（同事务写事件，relay 幂等发布）。

- Launch/取消/回归等状态变化与 Outbox 事件同事务写入；
- relay 以 ``producer_event_id`` 幂等：重复发布返回既有状态，不会重复投递；
- 发布失败保留 pending/failed 并记录 last_error，可由 Reconciler 重试。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

PENDING = "pending"
PUBLISHED = "published"
FAILED = "failed"
MAX_ATTEMPTS = 5


class AIQEOutbox(Base):
    __tablename__ = "aiqe_outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    producer_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    last_error: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_aiqe_outbox_producer_event", "producer_event_id", unique=True),
    )
