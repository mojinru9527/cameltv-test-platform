"""AITDE V3.2 DataSource repository (V32-001)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.data.models import DataSource


def create_data_source(
    db: Session, data: dict[str, Any], project_id: int, user_id: int
) -> DataSource:
    row = DataSource(project_id=project_id, created_by=user_id, **data)
    db.add(row)
    db.flush()
    return row


def get_data_source(
    db: Session, data_source_id: int, project_id: int
) -> DataSource | None:
    return db.scalar(
        select(DataSource).where(
            DataSource.id == data_source_id, DataSource.project_id == project_id
        )
    )


def list_data_sources(db: Session, project_id: int) -> list[DataSource]:
    rows = db.scalars(
        select(DataSource)
        .where(DataSource.project_id == project_id)
        .order_by(DataSource.id.asc())
    ).all()
    return list(rows)
