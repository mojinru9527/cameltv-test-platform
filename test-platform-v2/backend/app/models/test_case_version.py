"""测试用例版本历史模型 — 每次变更自动保存快照。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TestCaseVersion(Base):
    __tablename__ = "test_case_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(index=True)
    version_number: Mapped[int] = mapped_column(default=1)
    snapshot: Mapped[str] = mapped_column(Text, default="{}")  # JSON snapshot of TestCase fields
    changed_by: Mapped[int] = mapped_column(default=0)          # user_id who made the change
    changed_fields: Mapped[str] = mapped_column(default="")     # comma-separated field names
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
