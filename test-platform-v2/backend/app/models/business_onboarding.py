"""BusinessOnboarding — 新业务接入 4 步向导（B15）。

试点：basketball-service / camel-mimo。产出业务基线（版本验收任务）。
"""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class BusinessOnboarding(Base, TimestampMixin):
    __tablename__ = "business_onboarding"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    service_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    version: Mapped[str] = mapped_column(String(64), default="")
    requirement_text: Mapped[str] = mapped_column(Text, default="")
    api_spec_url: Mapped[str] = mapped_column(Text, default="")
    base_url: Mapped[str] = mapped_column(Text, default="")
    # draft | onboarding | active | blocked | archived
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    step: Mapped[int] = mapped_column(default=1)  # 1 登记 / 2 接基线 / 3 生成方案 / 4 跑基线
    version_task_id: Mapped[int | None] = mapped_column(index=True, default=None)
    baseline: Mapped[str] = mapped_column(Text, default="{}")
