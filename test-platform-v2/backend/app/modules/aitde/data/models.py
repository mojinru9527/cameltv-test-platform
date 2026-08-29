"""AITDE V3.2 DataSource model (V32-001).

A ``DataSource`` describes a typed, policy-constrained connection used by the
V3.2 data runtime: a static payload, a database (mysql/postgres), an API, or a
workflow. Only a ``secret_ref`` (a reference/key into an external secret store)
is persisted — the secret value itself is never stored on the row nor returned
through the API.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import (
    DataRequirementCleanupPolicy,
    DataRequirementSharingPolicy,
    DataSourceAccessMode,
    DataSourceStatus,
    DataSourceType,
)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    environment_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(32), default=DataSourceType.STATIC.value, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="")
    network_zone: Mapped[str] = mapped_column(String(64), default="")
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_mode: Mapped[str] = mapped_column(
        String(32), default=DataSourceAccessMode.READONLY.value, index=True
    )
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=DataSourceStatus.ACTIVE.value, index=True
    )
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    # created_at / updated_at from TimestampMixin


class DataRequirement(Base):
    """A scenario's declared business data requirement (V32-002).

    Describes *what* test data a scenario needs (``entity_type`` +
    ``constraints_json``) in business terms, not SQL. Bound to a frozen
    ``ScenarioVersion``.
    """

    __tablename__ = "data_requirements"
    __table_args__ = (
        UniqueConstraint(
            "scenario_version_id", "requirement_key", name="uq_data_req_scenario_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    requirement_key: Mapped[str] = mapped_column(String(128), default="")
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    # Business constraints, e.g. {"membership.status": "EXPIRED"} — never SQL.
    constraints_json: Mapped[str] = mapped_column(Text, default="{}")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    sharing_policy: Mapped[str] = mapped_column(
        String(32), default=DataRequirementSharingPolicy.EXCLUSIVE.value
    )
    cleanup_policy: Mapped[str] = mapped_column(
        String(32), default=DataRequirementCleanupPolicy.ALWAYS.value
    )
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
