"""执行节点注册表模型（batch-277 P0-5：由残留的 ``ai_job.py`` 更名而来）。

``ai_agents`` 表保留历史表名（生产已有节点数据，改名收益小于迁移风险）；
语义上它是**本地执行节点**（``cameltv-node``）的注册表，与已删除的 AI 任务
（旧 AI 任务表）无关。``X-AI-Agent-Token`` 鉴权见
``app/services/ai_agent_service.py``。

后续如需把表名改为 ``execution_nodes``，单独开迁移批次（需同步 token/审计引用）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ExecutionNode(Base, TimestampMixin):
    __tablename__ = "ai_agents"
    __table_args__ = (UniqueConstraint("agent_id", name="uq_ai_agent_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    project_scope: Mapped[int] = mapped_column(Integer, default=0, index=True)
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="online", index=True)
    last_health_at: Mapped[datetime | None] = mapped_column(default=None)
