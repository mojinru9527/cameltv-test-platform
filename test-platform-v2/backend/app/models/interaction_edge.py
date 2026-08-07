"""交互拓扑边（C120-1 全量入库，batch-113 3172 边）。"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class InteractionEdge(Base, TimestampMixin):
    __tablename__ = "interaction_edge"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    from_module: Mapped[str] = mapped_column(String(200), default="")
    entry: Mapped[str] = mapped_column(String(500), default="")
    to: Mapped[str] = mapped_column(String(500), default="", index=True)
    evidence: Mapped[str] = mapped_column(String(200), default="")
    source_batch: Mapped[str] = mapped_column(String(50), default="")
