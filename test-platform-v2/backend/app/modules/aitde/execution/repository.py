"""AITDE V3.1 execution repository (V31).

All queries honour the tenant boundary via ``project_id`` where the bound
aggregate has one. ScenarioAdapter is bound to a ScenarioVersion (project-scoped
through its scenario); EnvironmentSnapshot is mission-scoped.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.execution.models import (
    AssertionResult,
    EnvironmentSnapshot,
    ExecutionRun,
    ExecutionStep,
    ScenarioAdapter,
)
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion


# ── ScenarioAdapter ──────────────────────────────────────────────────────────


def validate_adapter_bind(
    db: Session, scenario_id: int, scenario_version_id: int, project_id: int
) -> None:
    """Reject a bind whose scenario/version do not belong to the caller's project."""
    scenario = db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )
    if not scenario:
        raise ValueError("SCENARIO_NOT_IN_PROJECT")
    version = db.scalar(
        select(TestScenarioVersion).where(
            TestScenarioVersion.id == scenario_version_id,
            TestScenarioVersion.scenario_id == scenario_id,
        )
    )
    if not version:
        raise ValueError("SCENARIO_VERSION_MISMATCH")


def get_adapter(
    db: Session, adapter_id: int, project_id: int
) -> ScenarioAdapter | None:
    """Return an adapter if its scenario belongs to the caller's project."""
    return db.scalar(
        select(ScenarioAdapter)
        .join(TestScenario, ScenarioAdapter.scenario_id == TestScenario.id)
        .where(
            ScenarioAdapter.id == adapter_id, TestScenario.project_id == project_id
        )
    )


def list_adapters(
    db: Session, scenario_id: int, project_id: int
) -> list[ScenarioAdapter]:
    return list(
        db.scalars(
            select(ScenarioAdapter)
            .join(TestScenario, ScenarioAdapter.scenario_id == TestScenario.id)
            .where(
                ScenarioAdapter.scenario_id == scenario_id,
                TestScenario.project_id == project_id,
            )
            .order_by(ScenarioAdapter.id.desc())
        ).all()
    )


def create_adapter(
    db: Session, data: dict[str, Any], user_id: int
) -> ScenarioAdapter:
    row = ScenarioAdapter(created_by=user_id, **data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def update_adapter(db: Session, row: ScenarioAdapter, data: dict[str, Any]) -> ScenarioAdapter:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── EnvironmentSnapshot ──────────────────────────────────────────────────────


def get_snapshot(db: Session, snapshot_id: int, project_id: int) -> EnvironmentSnapshot | None:
    from app.modules.aitde.mission.models import Mission

    return db.scalar(
        select(EnvironmentSnapshot)
        .join(Mission, EnvironmentSnapshot.mission_id == Mission.id)
        .where(
            EnvironmentSnapshot.id == snapshot_id, Mission.project_id == project_id
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


# ── ExecutionRun ─────────────────────────────────────────────────────────────


def get_run(db: Session, run_id: int, project_id: int) -> ExecutionRun | None:
    return db.scalar(
        select(ExecutionRun).where(
            ExecutionRun.id == run_id, ExecutionRun.project_id == project_id
        )
    )


def list_runs(
    db: Session,
    project_id: int,
    mission_id: int | None = None,
    outcome: str | None = None,
    runtime_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ExecutionRun], int]:
    from sqlalchemy import func

    stmt = select(ExecutionRun).where(ExecutionRun.project_id == project_id)
    count_stmt = select(func.count(ExecutionRun.id)).where(
        ExecutionRun.project_id == project_id
    )
    if mission_id is not None:
        stmt = stmt.where(ExecutionRun.mission_id == mission_id)
        count_stmt = count_stmt.where(ExecutionRun.mission_id == mission_id)
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


# ── ExecutionStep ────────────────────────────────────────────────────────────


def list_steps(db: Session, run_id: int, project_id: int) -> list[ExecutionStep]:
    """Steps are run-scoped; guard via the owning run's project."""
    return list(
        db.scalars(
            select(ExecutionStep)
            .join(ExecutionRun, ExecutionStep.run_id == ExecutionRun.id)
            .where(ExecutionStep.run_id == run_id, ExecutionRun.project_id == project_id)
            .order_by(ExecutionStep.sequence.asc())
        ).all()
    )


def add_step(db: Session, data: dict[str, Any]) -> ExecutionStep:
    row = ExecutionStep(**data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


# ── AssertionResult ──────────────────────────────────────────────────────────


def list_assertions(db: Session, run_id: int, project_id: int) -> list[AssertionResult]:
    return list(
        db.scalars(
            select(AssertionResult)
            .join(ExecutionRun, AssertionResult.run_id == ExecutionRun.id)
            .where(
                AssertionResult.run_id == run_id, ExecutionRun.project_id == project_id
            )
            .order_by(AssertionResult.id.asc())
        ).all()
    )


def add_assertion(db: Session, data: dict[str, Any]) -> AssertionResult:
    row = AssertionResult(**data)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row

