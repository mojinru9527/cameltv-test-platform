"""M2 / TA-015：节点能力清单模型（13 号 §4.22）。

- `available` 必须有 `last_evidence_ref` 支撑（自描述 + 实测 evidence）；
- capabilities_json 是能力 key 列表（如 browser.chromium / browser.webkit / db.readonly）。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class NodeCapabilityManifest(Base):
    __tablename__ = "node_capability_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    driver_key: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    driver_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    capabilities_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    platforms_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_parallel_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    artifact_types_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
