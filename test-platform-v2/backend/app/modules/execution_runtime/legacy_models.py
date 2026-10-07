"""Legacy Object Mapping 模型（平台简化批次收敛）。

``legacy_object_mappings`` 表保留：统一执行运行时（campaign_execution）依赖它
把旧 API 用例映射到 canonical Scenario（旧→新资产绑定）。其余 V40 cutover 表
（usage records / case migrations / cutover batches）已随 AITDE 删除。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.execution_runtime.legacy_enums import LegacyObjectType, MigrationStatus


class LegacyObjectMapping(Base):
    """V40-002: a verified bidirectionality-preserving mapping legacy -> canonical.

    ``UNIQUE(legacy_type, legacy_id)`` keeps the mapping idempotent: a legacy
    object maps to exactly one canonical object and may be migrated once.
    ``migration_status`` follows :class:`MigrationStatus` and ``verified_at`` is
    only set once a post-migration equivalence check passes.
    """

    __tablename__ = "legacy_object_mappings"
    __table_args__ = (
        UniqueConstraint(
            "legacy_type", "legacy_id", name="uq_legacy_object_mapping"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    legacy_type: Mapped[str] = mapped_column(
        String(32), default=LegacyObjectType.TEST_CASE.value, index=True
    )
    legacy_id: Mapped[int] = mapped_column(Integer, index=True)
    canonical_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    canonical_id: Mapped[int] = mapped_column(Integer, index=True)
    migration_status: Mapped[str] = mapped_column(
        String(16), default=MigrationStatus.PENDING.value, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
