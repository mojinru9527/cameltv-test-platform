"""AITDE V3.3 CommandPlan models (V33-002)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import CommandPlanStatus


class CommandPlan(Base):
    __tablename__ = "command_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_adapter_id: Mapped[int] = mapped_column(Integer, index=True)
    current_version_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class CommandPlanVersion(Base):
    __tablename__ = "command_plan_versions"
    __table_args__ = (
        UniqueConstraint("command_plan_id", "version_no", name="uq_command_plan_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    command_plan_id: Mapped[int] = mapped_column(Integer, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    contract_version_id: Mapped[int] = mapped_column(Integer, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
    plan_json: Mapped[str] = mapped_column(Text, default="{}")
    plan_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=CommandPlanStatus.DRAFT.value, index=True
    )
    generated_by_type: Mapped[str] = mapped_column(String(16), default="AI")
    model_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
