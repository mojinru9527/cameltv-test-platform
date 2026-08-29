"""AITDE V3.2 DataSource repository (V32-001)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.data.models import (
    CleanupRecord,
    DataFixture,
    DataPlan,
    DataPlanStep,
    DataRequirement,
    DataSnapshot,
    DataSource,
    FixtureEntity,
    FixtureLease,
    LegacyDatasetLink,
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


# ────────────────────────────────────────────────────────────────────────────
# Fixture / Lease / Snapshot / Cleanup (V32-009..V32-012)
# ────────────────────────────────────────────────────────────────────────────


def create_fixture(db: Session, data: dict[str, Any]) -> DataFixture:
    row = DataFixture(**data)
    db.add(row)
    db.flush()
    return row


def get_fixture(db: Session, fixture_id: int) -> DataFixture | None:
    return db.get(DataFixture, fixture_id)


def list_fixture_entities(db: Session, fixture_id: int) -> list[FixtureEntity]:
    rows = db.scalars(
        select(FixtureEntity)
        .where(FixtureEntity.fixture_id == fixture_id)
        .order_by(FixtureEntity.id.asc())
    ).all()
    return list(rows)


def create_fixture_entity(db: Session, data: dict[str, Any]) -> FixtureEntity:
    row = FixtureEntity(**data)
    db.add(row)
    db.flush()
    return row


def create_fixture_lease(
    db: Session, data: dict[str, Any]
) -> FixtureLease:
    row = FixtureLease(**data)
    db.add(row)
    db.flush()
    return row


def get_active_lease_for_fixture(
    db: Session, fixture_id: int
) -> FixtureLease | None:
    return db.scalar(
        select(FixtureLease).where(
            FixtureLease.fixture_id == fixture_id,
            FixtureLease.status == "ACTIVE",
        )
    )


def create_snapshot(db: Session, data: dict[str, Any]) -> DataSnapshot:
    row = DataSnapshot(**data)
    db.add(row)
    db.flush()
    return row


def list_snapshots(db: Session, fixture_id: int) -> list[DataSnapshot]:
    rows = db.scalars(
        select(DataSnapshot)
        .where(DataSnapshot.fixture_id == fixture_id)
        .order_by(DataSnapshot.id.asc())
    ).all()
    return list(rows)


def create_cleanup_record(db: Session, data: dict[str, Any]) -> CleanupRecord:
    row = CleanupRecord(**data)
    db.add(row)
    db.flush()
    return row


def get_latest_cleanup_record(
    db: Session, fixture_id: int
) -> CleanupRecord | None:
    return db.scalar(
        select(CleanupRecord)
        .where(CleanupRecord.fixture_id == fixture_id)
        .order_by(CleanupRecord.attempt_no.desc())
    )


# ────────────────────────────────────────────────────────────────────────────
# Legacy dataset link (V32-015)
# ────────────────────────────────────────────────────────────────────────────


def create_legacy_link(
    db: Session, data: dict[str, Any]
) -> LegacyDatasetLink:
    row = LegacyDatasetLink(**data)
    db.add(row)
    db.flush()
    return row


def get_legacy_link_by_dataset(
    db: Session, legacy_dataset_id: int
) -> LegacyDatasetLink | None:
    return db.scalar(
        select(LegacyDatasetLink).where(
            LegacyDatasetLink.legacy_dataset_id == legacy_dataset_id
        )
    )
