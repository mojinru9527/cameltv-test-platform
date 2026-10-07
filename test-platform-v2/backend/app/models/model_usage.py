"""AI 用量台账模型（从 AITDE governance 抽离，AI 额度闸门保留）。

表名 ``model_usage_ledger`` 与既有迁移一致；``app/services/ai_guard.py`` 每次 LLM
调用按 (project_id, created_at) 统计近 60s 行数与近 24h token 之和。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelUsageLedger(Base):
    """Per-operation model/runtime usage + cost accounting (V40-015)."""

    __tablename__ = "model_usage_ledger"
    __table_args__ = (
        Index("ix_model_usage_project_created", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    operation_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    model_ref: Mapped[str] = mapped_column(String(128), default="")
    input_units: Mapped[int] = mapped_column(Integer, default=0)
    output_units: Mapped[int] = mapped_column(Integer, default=0)
    cost_amount: Mapped[float | None] = mapped_column(default=None)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
