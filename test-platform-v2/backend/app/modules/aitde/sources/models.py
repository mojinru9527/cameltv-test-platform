"""Source normalization models (V30-020).

Represents a Mission's raw input as normalized artifacts + fragments:
- ``SourceArtifact`` — one ingested source (PRD / OpenAPI / manual note…)
- ``SourceFragment`` — a stable, hash-addressed chunk with a location ref
- ``MissionSourceLink`` — which artifacts feed a Mission and in what role
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import ParseStatus


class SourceArtifact(Base, TimestampMixin):
    __tablename__ = "source_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    provider: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    version_label: Mapped[str] = mapped_column(String(64), default="")
    sensitivity: Mapped[str] = mapped_column(String(32), default="normal")
    parse_status: Mapped[str] = mapped_column(
        String(32), default=ParseStatus.PENDING.value, index=True
    )
    normalized_text: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    # created_at / updated_at from TimestampMixin


class SourceFragment(Base):
    __tablename__ = "source_fragments"
    __table_args__ = (
        UniqueConstraint("artifact_id", "fragment_key", name="uq_source_fragment_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(Integer, index=True)
    fragment_key: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    location_json: Mapped[str] = mapped_column(Text, default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class MissionSourceLink(Base):
    __tablename__ = "mission_source_links"
    __table_args__ = (
        UniqueConstraint("mission_id", "artifact_id", name="uq_mission_source_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    artifact_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(32), default="REQUIREMENT")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
