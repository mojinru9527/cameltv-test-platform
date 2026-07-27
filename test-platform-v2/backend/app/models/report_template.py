"""ReportTemplate — 可配置的报告内容板块模板。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Default sections for a standard report template
DEFAULT_SECTIONS = [
    {"key": "stats",       "label": "统计概览", "enabled": True,  "order": 1},
    {"key": "cases",       "label": "用例明细", "enabled": True,  "order": 2},
    {"key": "defects",     "label": "缺陷列表", "enabled": True,  "order": 3},
    {"key": "gate",        "label": "门禁结果", "enabled": True,  "order": 4},
    {"key": "trend",       "label": "趋势对比", "enabled": False, "order": 5},
    {"key": "description", "label": "备注信息", "enabled": True,  "order": 0},
]

AVAILABLE_SECTION_KEYS = [s["key"] for s in DEFAULT_SECTIONS]


class ReportTemplate(Base):
    __tablename__ = "report_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(String(500), default="")
    # JSON array of {"key", "label", "enabled", "order"} objects
    sections: Mapped[str] = mapped_column(Text, default="[]")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
