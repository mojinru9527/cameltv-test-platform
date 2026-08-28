"""Mission repository (V30-011).

All queries are scoped to a project to honour the platform's tenant boundary.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.aitde.mission.models import Mission


def _build_mission_key(db: Session, project_id: int) -> str:
    """Generate a unique, sequential mission key for a project (M-{project}-{n})."""
    count = db.scalar(
        select(func.count(Mission.id)).where(Mission.project_id == project_id)
    ) or 0
    return f"M-{project_id}-{count + 1:04d}"


def get(db: Session, mission_id: int, project_id: int) -> Mission | None:
    return db.scalar(
        select(Mission).where(
            Mission.id == mission_id, Mission.project_id == project_id
        )
    )


def list_missions(
    db: Session,
    project_id: int,
    status: str | None = None,
    mission_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Mission], int]:
    stmt = select(Mission).where(Mission.project_id == project_id)
    count_stmt = select(func.count(Mission.id)).where(Mission.project_id == project_id)
    if status:
        stmt = stmt.where(Mission.status == status)
        count_stmt = count_stmt.where(Mission.status == status)
    if mission_type:
        stmt = stmt.where(Mission.mission_type == mission_type)
        count_stmt = count_stmt.where(Mission.mission_type == mission_type)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(Mission.title.like(like) | Mission.mission_key.like(like))
        count_stmt = count_stmt.where(
            Mission.title.like(like) | Mission.mission_key.like(like)
        )
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(Mission.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(items), total


def create(db: Session, data: dict[str, Any], project_id: int, user_id: int) -> Mission:
    row = Mission(project_id=project_id, created_by=user_id, **data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, row: Mission, data: dict[str, Any]) -> Mission:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def archive(db: Session, row: Mission) -> Mission:
    from datetime import datetime

    from app.modules.aitde.common.enums import MissionStatus

    row.status = MissionStatus.ARCHIVED.value
    row.archived_at = datetime.now()
    db.commit()
    db.refresh(row)
    return row
