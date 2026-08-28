"""Mission aggregate model (V30-010).

``Mission`` replaces the legacy ``VersionMission`` as the canonical test-domain
aggregate. It is intentionally slim: sources, contract, scenarios and plans are
kept in relation tables rather than a fat ``scope`` JSON column.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import AcceptanceStatus, MissionStatus, MissionType


class Mission(Base, TimestampMixin):
    __tablename__ = "missions"
    __table_args__ = (
        UniqueConstraint("project_id", "mission_key", name="uq_mission_project_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_key: Mapped[str] = mapped_column(String(64), default="")
    mission_type: Mapped[str] = mapped_column(
        String(32), default=MissionType.VERSION.value, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="")
    version_label: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[str] = mapped_column(
        String(32), default=MissionStatus.DRAFT.value, index=True
    )
    owner_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    qa_owner_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    default_environment_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    current_contract_version_id: Mapped[int | None] = mapped_column(
        Integer, default=None
    )
    acceptance_status: Mapped[str] = mapped_column(
        String(32), default=AcceptanceStatus.NOT_EVALUATED.value
    )
    legacy_version_mission_id: Mapped[int | None] = mapped_column(
        Integer, default=None, unique=True
    )
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
