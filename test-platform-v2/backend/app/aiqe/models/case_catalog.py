"""V16-014-R2：Case/Workflow Catalog（A5 impact → mandatory scope 的映射事实源）。

- 每条记录把业务 Case/Node 与 route/file/symbol/OpenAPI operation 关联；
- 只允许人工/导入维护（服务端校验 project 归属），A5 只读匹配、不能自行缩小范围；
- A5 UNKNOWN 时按项目全部 catalog 节点扩大回归。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CaseCatalogEntry(Base):
    __tablename__ = "aiqe_case_catalog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(String(120), nullable=False)
    node_key: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    workflow_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    api_operation: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("project_id", "case_id", name="uq_aiqe_case_catalog_case"),
        Index("ix_aiqe_case_catalog_project_node", "project_id", "node_key"),
    )
