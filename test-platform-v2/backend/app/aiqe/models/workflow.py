"""M2 / TA-010：Workflow 定义 + 资源锁模型。

- workflow_definitions（13 号 §4.6）：approved 后 graph_json/checksum 冻结；
- resource_locks（§6.4）：key 级锁 + TTL + fencing token（单调递增）。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("test_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    #: V16-001 §5：旧 Workflow 的策略迁移状态。
    #: UNREVIEWED（未核对）/ MIGRATED（旧字段已迁入服务端策略）/ NEEDS_POLICY_REVIEW（无法自动映射，禁止调度）。
    policy_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="UNREVIEWED"
    )
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("scenario_id", "version", name="uq_workflow_scenario_version"),
    )


class ResourceLock(Base):
    """资源锁行；release 只把 expires_at 置为过期，保留 fencing token 单调性。"""

    __tablename__ = "resource_locks"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    fencing_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

class WorkflowSnapshot(Base):
    """V16-007：不可变 Workflow 冻结快照（执行唯一可绑定对象）。

    - ``canonical_json``：排序键的规范化 graph，保证 checksum 可复算；
    - ``checksum_sha256``：canonical JSON 的 sha256；
    - 绑定当时的 TargetPolicy / Query Registry / Driver Manifest 版本，便于事后复算；
    - 一旦写入不可修改（无 update 路径）；克隆产生新快照并记录 parent。
    """

    __tablename__ = "aiqe_workflow_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    canonical_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: V16-007 §6：clone diff（被排除节点、重写依赖、删除边及原因）。
    clone_diff_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    execution_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    target_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_policy_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    query_registry_version: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    driver_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        # 唯一索引（而非 UniqueConstraint）：SQLite 无法 ALTER TABLE ADD CONSTRAINT。
        Index(
            "uq_aiqe_workflow_snapshots_content",
            "project_id",
            "workflow_id",
            "checksum_sha256",
            "execution_kind",
            unique=True,
        ),
        Index("ix_aiqe_workflow_snapshots_workflow", "project_id", "workflow_id"),
    )
