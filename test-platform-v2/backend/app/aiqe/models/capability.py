"""M2 / TA-015 + AUD-005：节点能力清单模型（13 号 §4.22）。

AUD-005 起增加 6 态 ``capability_status``（v1.5 §01）：
REGISTERED / AVAILABLE / VERIFIED / DEGRADED / UNAVAILABLE / REVOKED。

- ``available`` 保留为派生投影（= AVAILABLE 或 VERIFIED），兼容既有查询；
- ``verified_platforms_json`` 记录真正跑过验收的平台，是 VERIFIED 的证据；
- ``runner_version`` / ``driver_version`` 变化会使 VERIFIED 失效，必须重新验收。
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
    runner_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    manifest_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    manifest_signature: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    capabilities_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    platforms_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    verified_platforms_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_parallel_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    artifact_types_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: 6 态能力状态（AUD-005）；`available` 是它的派生投影。
    capability_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="REGISTERED", index=True
    )
    status_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
