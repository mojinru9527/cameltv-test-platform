"""Batch 258 / B1-4 — 本地执行节点任务协议（ExecutionJob）。

与 `AiJob` **并列、不合并**（09-platform-landing-plan.md §3.2）：`AiJob` 承载「本地 AI 推理」，
`ExecutionJob` 承载「本地测试执行」（接口 httpx / Web Playwright）。控制面只做
登记 · 调度 · 聚合证据，不执行（ADR-0026 §3.1 职责边界）。

租约字段**内联在本表**（`node_id` / `claimed_at` / `lease_expires_at` / `heartbeat_at`），
沿用 `AiJob` 的 claim/heartbeat/stale 语义；不另建 `job_leases` 表——同一份租约两处记账
是双栈漂移的经典来源，而 `AiJob` 的先例也是内联。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ExecutionJob(Base, TimestampMixin):
    __tablename__ = "execution_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    kind: Mapped[str] = mapped_column(String(16), default="api", index=True)  # api | web
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    case_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    env_ref: Mapped[str] = mapped_column(String(255), default="")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    # ── 租约（claim / heartbeat / stale 回收）──
    node_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(default=None)
    lease_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    heartbeat_at: Mapped[datetime | None] = mapped_column(default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    # ── 产出（B4 证据链的挂点）──
    evidence_bundle_id: Mapped[int | None] = mapped_column(default=None)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
