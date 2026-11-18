"""M4 / TA-027.3 + AUD-019：Noise Suppression Rules 模型。

规则必须有到期时间（默认 90 天），到期后强制复核；禁止永久 quarantine。

AUD-019 治理字段（v1.5 §04-9）：project scope / environment / profile / detector|error class /
selector / 适用版本 / evidence refs / created_by / approved_by / valid_from / expires_at /
reason / matched_count / false_suppress_count / version（续期新建版本）。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class NoiseRule(Base):
    __tablename__ = "noise_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="suppress")
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="run")
    # ── AUD-019 治理字段 ──
    environment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detector_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selector_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    false_suppress_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_approval")
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
