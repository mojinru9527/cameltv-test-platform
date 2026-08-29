"""AITDE V3.2 DataSource model (V32-001).

A ``DataSource`` describes a typed, policy-constrained connection used by the
V3.2 data runtime: a static payload, a database (mysql/postgres), an API, or a
workflow. Only a ``secret_ref`` (a reference/key into an external secret store)
is persisted — the secret value itself is never stored on the row nor returned
through the API.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import (
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
