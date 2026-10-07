"""执行运行时数据访问（从 AITDE execution.repository 抽离的最小集）。

仅保留统一执行链路所需函数：Run/快照的创建、读取与分页列表。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.execution_runtime.models import EnvironmentSnapshot, ExecutionRun


def get_snapshot(db: Session, snapshot_id: int, project_id: int) -> EnvironmentSnapshot | None:
    return db.scalar(
        select(EnvironmentSnapshot).where(
            EnvironmentSnapshot.id == snapshot_id,
        )
    )


def create_snapshot(
    db: Session, data: dict[str, Any], environment_id: int, mission_id: int
) -> EnvironmentSnapshot:
    row = EnvironmentSnapshot(environment_id=environment_id, mission_id=mission_id, **data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def latest_snapshot(
    db: Session, environment_id: int, mission_id: int
) -> EnvironmentSnapshot | None:
    return db.scalar(
        select(EnvironmentSnapshot)
        .where(
            EnvironmentSnapshot.environment_id == environment_id,
            EnvironmentSnapshot.mission_id == mission_id,
        )
        .order_by(EnvironmentSnapshot.id.desc())
        .limit(1)
    )


def get_run(db: Session, run_id: int, project_id: int) -> ExecutionRun | None:
    return db.scalar(
        select(ExecutionRun).where(
            ExecutionRun.id == run_id, ExecutionRun.project_id == project_id
        )
    )


def list_runs(
    db: Session,
    project_id: int,
    campaign_id: int | None = None,
    outcome: str | None = None,
    runtime_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ExecutionRun], int]:
    stmt = select(ExecutionRun).where(ExecutionRun.project_id == project_id)
    count_stmt = select(func.count(ExecutionRun.id)).where(
        ExecutionRun.project_id == project_id
    )
    if campaign_id is not None:
        stmt = stmt.where(ExecutionRun.campaign_id == campaign_id)
        count_stmt = count_stmt.where(ExecutionRun.campaign_id == campaign_id)
    if outcome:
        stmt = stmt.where(ExecutionRun.outcome == outcome)
        count_stmt = count_stmt.where(ExecutionRun.outcome == outcome)
    if runtime_status:
        stmt = stmt.where(ExecutionRun.runtime_status == runtime_status)
        count_stmt = count_stmt.where(ExecutionRun.runtime_status == runtime_status)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(ExecutionRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def create_run(db: Session, data: dict[str, Any], user_id: int) -> ExecutionRun:
    row = ExecutionRun(created_by=user_id, **data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def update_run(db: Session, row: ExecutionRun, data: dict[str, Any]) -> ExecutionRun:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
