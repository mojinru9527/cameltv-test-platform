"""AITDE V3.3 Browser session models (V33-006)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import BrowserSessionMode


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    environment_id: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(
        String(16), default=BrowserSessionMode.OBSERVE.value, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    browser_type: Mapped[str] = mapped_column(String(16), default="chromium")
    context_ref: Mapped[str] = mapped_column(String(255), default="")
    started_by: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class BrowserObservationEvent(Base):
    __tablename__ = "browser_observation_events"
    __table_args__ = (
        UniqueConstraint("browser_session_id", "sequence", name="uq_observation_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    browser_session_id: Mapped[int] = mapped_column(Integer, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    semantic_target_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_ref_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)
