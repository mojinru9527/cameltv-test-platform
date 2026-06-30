"""测试计划 + 计划用例关联 + 执行记录 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TestPlan(Base):
    __tablename__ = "test_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    plan_id: Mapped[str] = mapped_column(default="")
    name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="draft")  # draft/active/completed/archived
    creator_id: Mapped[int] = mapped_column(default=0)
    start_date: Mapped[Optional[datetime]] = mapped_column(default=None)
    end_date: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    # relations
    plan_cases: Mapped[list["TestPlanCase"]] = relationship(
        "TestPlanCase", back_populates="plan",
        cascade="all, delete-orphan", order_by="TestPlanCase.sort_order",
    )


class TestPlanCase(Base):
    __tablename__ = "test_plan_case"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("test_plan.id"), index=True)
    case_id: Mapped[int] = mapped_column(default=0, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    last_status: Mapped[str] = mapped_column(default="pending")  # pending/pass/fail/skip/block
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    executor_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # relations
    plan: Mapped["TestPlan"] = relationship("TestPlan", back_populates="plan_cases")
    executions: Mapped[list["TestExecution"]] = relationship(
        "TestExecution", back_populates="plan_case",
        cascade="all, delete-orphan", order_by="TestExecution.executed_at.desc()",
    )


class TestExecution(Base):
    __tablename__ = "test_execution"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_case_id: Mapped[int] = mapped_column(ForeignKey("test_plan_case.id"), index=True)
    executor_id: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="pending")  # pass/fail/skip/block/pending
    actual_result: Mapped[str] = mapped_column(default="")
    notes: Mapped[str] = mapped_column(default="")
    trace_id: Mapped[str] = mapped_column(default="")       # ELK traceId
    executed_at: Mapped[datetime] = mapped_column(default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # relations
    plan_case: Mapped["TestPlanCase"] = relationship("TestPlanCase", back_populates="executions")
