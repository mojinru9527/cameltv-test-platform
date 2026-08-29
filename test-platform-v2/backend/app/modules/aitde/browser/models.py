"""AITDE V3.3 Browser session models (V33-006) + healing proposal (V33-011)
+ legacy UI asset binding (plan §2)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import (
    BrowserSessionMode,
    HealingProposalStatus,
    UiAssetBindingStatus,
)


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
        UniqueConstraint(
            "browser_session_id", "sequence", name="uq_observation_sequence"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    browser_session_id: Mapped[int] = mapped_column(Integer, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    semantic_target_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_ref_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)


class HealingProposal(Base):
    __tablename__ = "healing_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_adapter_id: Mapped[int] = mapped_column(Integer, index=True)
    command_plan_version_id: Mapped[int] = mapped_column(Integer, index=True)
    proposal_type: Mapped[str] = mapped_column(String(32), index=True)
    before_json: Mapped[str] = mapped_column(Text, default="{}")
    after_json: Mapped[str] = mapped_column(Text, default="{}")
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(
        String(16), default=HealingProposalStatus.OPEN.value, index=True
    )
    created_by_type: Mapped[str] = mapped_column(String(16), default="AI")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class UiAssetBinding(Base):
    __tablename__ = "ui_asset_bindings"
    __table_args__ = (
        UniqueConstraint(
            "scenario_adapter_id", "legacy_ui_case_id", name="uq_ui_asset_binding"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_adapter_id: Mapped[int] = mapped_column(Integer, index=True)
    legacy_ui_case_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    legacy_ui_script_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    binding_status: Mapped[str] = mapped_column(
        String(16), default=UiAssetBindingStatus.UNBOUND.value, index=True
    )
