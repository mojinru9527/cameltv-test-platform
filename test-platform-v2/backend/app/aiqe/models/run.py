"""M1 / TA-005：Run 事实源模型。

四张表对应 13 号 §4.7-§4.10：
- test_runs：通用执行实例（事实源）
- node_runs：DAG 节点执行事实，1:1 关联旧 execution_jobs
- step_attempts：步骤尝试（永久保留，重试追加）
- assertion_results：断言结果（必须脱敏）

ID 规则（13 号 §4）：新实体 UUID（String(36) 以兼容 SQLite/PG），旧表外键 BIGINT。
scenario_id / workflow_definition_id / execution_profile_id 暂不建 FK（对应表在 M2 创建），
M2 建表后补 FK。
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False
    )
    run_key: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scenario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("test_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    workflow_definition_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    build_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    environment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("environment.id", ondelete="SET NULL"), nullable=True
    )
    execution_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    environment_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    retest_of: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    trigger_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    node_runs: Mapped[list[NodeRun]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "run_key", name="uq_test_runs_project_run_key"),
        Index("ix_test_runs_project_created", "project_id", "created_at"),
        Index("ix_test_runs_scenario_created", "scenario_id", "created_at"),
        Index("ix_test_runs_commit_sha", "commit_sha"),
        Index("ix_test_runs_retest_of", "retest_of"),
        Index("ix_test_runs_status", "status"),
    )


class NodeRun(Base):
    __tablename__ = "node_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_key: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_key: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING", index=True)
    input_ref: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_ref: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_class: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    resource_keys_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    execution_job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("execution_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    run: Mapped[TestRun] = relationship(back_populates="node_runs")
    step_attempts: Mapped[list[StepAttempt]] = relationship(
        back_populates="node_run", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("run_id", "node_key", name="uq_node_runs_run_node"),)


class StepAttempt(Base):
    __tablename__ = "step_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    node_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("node_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    external_execution_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    node_run: Mapped[NodeRun] = relationship(back_populates="step_attempts")
    assertion_results: Mapped[list[RunAssertionResult]] = relationship(
        back_populates="step_attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "node_run_id", "step_key", "attempt_no", name="uq_step_attempts_node_step_attempt"
        ),
    )


class RunAssertionResult(Base):
    # 既有 assertion_results 表属于 execution_runtime（AITDE，7654 行，schema 不同），
    # M1 新建独立表避免同名冲突；待 legacy 退役后再评估合并（D-279-1）。
    __tablename__ = "run_assertion_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    step_attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("step_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assertion_key: Mapped[str] = mapped_column(String(100), nullable=False)
    assertion_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_EVALUATED")
    expected_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    actual_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    diff_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    evidence_refs_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    evaluated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="deterministic")

    step_attempt: Mapped[StepAttempt] = relationship(back_populates="assertion_results")

    __table_args__ = (
        UniqueConstraint(
            "step_attempt_id", "assertion_key", name="uq_assertion_results_attempt_assertion"
        ),
    )
