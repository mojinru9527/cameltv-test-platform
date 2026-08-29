"""AITDE V3.2 DataSource repository (V32-001)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.data.models import DataRequirement, DataSource


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


# ────────────────────────────────────────────────────────────────────────────
# DataRequirement (V32-002)
# ────────────────────────────────────────────────────────────────────────────


def list_requirements_by_scenario_version(
    db: Session, scenario_version_id: int
) -> list[DataRequirement]:
    rows = db.scalars(
        select(DataRequirement)
        .where(DataRequirement.scenario_version_id == scenario_version_id)
        .order_by(DataRequirement.id.asc())
    ).all()
    return list(rows)


def get_data_requirement(db: Session, requirement_id: int) -> DataRequirement | None:
    return db.get(DataRequirement, requirement_id)


def create_data_requirement(
    db: Session, scenario_version_id: int, data: dict[str, Any]
) -> DataRequirement:
    row = DataRequirement(scenario_version_id=scenario_version_id, **data)
    db.add(row)
    db.flush()
    return row
