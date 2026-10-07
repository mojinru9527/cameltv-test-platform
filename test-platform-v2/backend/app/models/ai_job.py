"""执行节点注册表模型（平台简化批次：AiJob/AiResult 已随 AI 本地管线删除）。

``ai_agents`` 表保留——本地执行节点（cameltv-node）注册与在线状态仍依赖它；
``X-AI-Agent-Token`` 鉴权见 ``app/services/ai_agent_service.py``。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiAgent(Base, TimestampMixin):
    __tablename__ = "ai_agents"
    __table_args__ = (UniqueConstraint("agent_id", name="uq_ai_agent_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    project_scope: Mapped[int] = mapped_column(Integer, default=0, index=True)
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="online", index=True)
    last_health_at: Mapped[datetime | None] = mapped_column(default=None)
