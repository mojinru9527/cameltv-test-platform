"""AITDE V3.2 DataSource repository (V32-001)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.data.models import (
    DataPlan,
    DataPlanStep,
    DataRequirement,
    DataSource,
)


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


# ────────────────────────────────────────────────────────────────────────────
# DataPlan / Step (V32-003)
# ────────────────────────────────────────────────────────────────────────────


def create_data_plan(db: Session, data: dict[str, Any]) -> DataPlan:
    row = DataPlan(**data)
    db.add(row)
    db.flush()
    return row


def get_data_plan(db: Session, plan_id: int) -> DataPlan | None:
    return db.get(DataPlan, plan_id)


def list_data_plans_by_scenario_version(
    db: Session, scenario_version_id: int
) -> list[DataPlan]:
    rows = db.scalars(
        select(DataPlan)
        .where(DataPlan.scenario_version_id == scenario_version_id)
        .order_by(DataPlan.id.asc())
    ).all()
    return list(rows)


def create_data_plan_step(
    db: Session, data: dict[str, Any]
) -> DataPlanStep:
    row = DataPlanStep(**data)
    db.add(row)
    db.flush()
    return row


def list_steps_by_plan(db: Session, plan_id: int) -> list[DataPlanStep]:
    rows = db.scalars(
        select(DataPlanStep)
        .where(DataPlanStep.data_plan_id == plan_id)
        .order_by(DataPlanStep.sequence.asc())
    ).all()
    return list(rows)
