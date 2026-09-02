"""VersionTask — 版本验收任务：唯一事实源（Batch 216 / B6）。

以「版本」为唯一主线，把 需求源 → 验收方案 → 执行记录 → 缺陷 → 放行结论
收束为一条可追踪的数据脊梁。旧数据（VersionMission / TestPlan / ReleaseBundle）
通过 source / source_mission_id 只读兼容映射，不双写。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class VersionTask(Base, TimestampMixin):
    """版本验收任务（唯一事实源）。

    状态机（VersionTaskService.TRANSITIONS）：
      draft → plan_review → approved → executing → executed → verdict → released
      任意非终态可转 blocked / cancelled。
    """
    __tablename__ = "version_task"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_version_task_project_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)

    # ── 标识 ──
    title: Mapped[str] = mapped_column(String(300), default="")
    version: Mapped[str] = mapped_column(String(80), default="", index=True)
    # 来源：manual（新建）/ mission（旧智能测试任务导入兼容）/ bundle（发布包派生）
    source: Mapped[str] = mapped_column(String(20), default="manual", index=True)
    # 旧数据只读兼容映射指针（不双写）
    source_mission_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_mission.id", ondelete="SET NULL"), default=None, index=True
    )
    source_bundle_id: Mapped[int | None] = mapped_column(
        ForeignKey("release_bundle.id", ondelete="SET NULL"), default=None, index=True
    )

    # ── 关联（主链路各环节的事实源指针）──
    requirement_doc_id: Mapped[int | None] = mapped_column(
        ForeignKey("requirement_document.id", ondelete="SET NULL"), default=None, index=True
    )
    release_bundle_id: Mapped[int | None] = mapped_column(
        ForeignKey("release_bundle.id", ondelete="SET NULL"), default=None, index=True
    )
    environment_id: Mapped[int | None] = mapped_column(default=None, index=True)

    # ── 状态机 / 结论 ──
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    verdict: Mapped[str] = mapped_column(
        String(20), default="", index=True
    )  # "" | pass | blocked | conditional（放行 / 打回 / 有条件）
    coverage: Mapped[str] = mapped_column(Text, default="{}")  # {pass/fail/skip/blocked 计数}
    summary: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(Text, default="{}")  # 变更范围 / 验收点
    risk: Mapped[str] = mapped_column(Text, default="{}")  # 放行风险列表

    # ── 所有权 ──
    created_by: Mapped[int] = mapped_column(default=0, index=True)
    qa_owner_id: Mapped[int] = mapped_column(default=0, index=True)

    # ── ORM 关系（便于证据包读取）──
    executions: Mapped[list["VersionTaskExecution"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="VersionTaskExecution.id"
    )
    defects: Mapped[list["VersionTaskDefect"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="VersionTaskDefect.id"
    )


class VersionTaskExecution(Base, TimestampMixin):
    """版本任务 ↔ 执行记录 关联（多态：runner / apitest / uitest / mission_scenario）。"""
    __tablename__ = "version_task_execution"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("version_task.id", ondelete="CASCADE"), index=True)
    execution_type: Mapped[str] = mapped_column(String(30), default="runner", index=True)
    execution_id: Mapped[int] = mapped_column(default=0, index=True)
    ref: Mapped[str] = mapped_column(String(120), default="")  # 外部回放/证据引用

    task: Mapped[VersionTask] = relationship(back_populates="executions")


class VersionTaskDefect(Base, TimestampMixin):
    """版本任务 ↔ 缺陷 关联（业务失败一键转缺陷草稿）。"""
    __tablename__ = "version_task_defect"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("version_task.id", ondelete="CASCADE"), index=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id", ondelete="CASCADE"), index=True)

    task: Mapped[VersionTask] = relationship(back_populates="defects")
