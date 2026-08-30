"""AITDE V3.5 Continuous Acceptance repository (V35).

CRUD for the Continuous Acceptance tables. All queries honour the tenant
boundary via ``project_id`` where the aggregate has one.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.continuous.models import (
    BuildObservation,
    CampaignScenario,
    EnvironmentFingerprint,
    ExecutionCampaign,
    QualityGatePolicy,
    QualityGateResultRecord,
    RunProfile,
    Trigger,
)


# ── EnvironmentFingerprint ───────────────────────────────────────────────────


def get_fingerprint_by_hash(
    db: Session, environment_id: int, fingerprint_hash: str
) -> EnvironmentFingerprint | None:
    return db.scalar(
        select(EnvironmentFingerprint).where(
            EnvironmentFingerprint.environment_id == environment_id,
            EnvironmentFingerprint.fingerprint_hash == fingerprint_hash,
        )
    )


def create_fingerprint(db: Session, data: dict[str, Any]) -> EnvironmentFingerprint:
    row = EnvironmentFingerprint(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_fingerprints(
    db: Session, environment_id: int, limit: int = 20
) -> list[EnvironmentFingerprint]:
    return list(
        db.scalars(
            select(EnvironmentFingerprint)
            .where(EnvironmentFingerprint.environment_id == environment_id)
            .order_by(EnvironmentFingerprint.id.desc())
            .limit(limit)
        ).all()
    )


# ── BuildObservation ─────────────────────────────────────────────────────────


def get_build_observation(
    db: Session, observation_id: int, mission_id: int
) -> BuildObservation | None:
    return db.scalar(
        select(BuildObservation).where(
            BuildObservation.id == observation_id, BuildObservation.mission_id == mission_id
        )
    )


def find_latest_build_observation(
    db: Session, environment_id: int, mission_id: int
) -> BuildObservation | None:
    return db.scalar(
        select(BuildObservation)
        .where(
            BuildObservation.environment_id == environment_id,
            BuildObservation.mission_id == mission_id,
        )
        .order_by(BuildObservation.id.desc())
        .limit(1)
    )


def create_build_observation(db: Session, data: dict[str, Any]) -> BuildObservation:
    row = BuildObservation(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_build_observation(
    db: Session, row: BuildObservation, data: dict[str, Any]
) -> BuildObservation:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def list_build_observations(
    db: Session, mission_id: int, limit: int = 50
) -> list[BuildObservation]:
    return list(
        db.scalars(
            select(BuildObservation)
            .where(BuildObservation.mission_id == mission_id)
            .order_by(BuildObservation.id.desc())
            .limit(limit)
        ).all()
    )


# ── ExecutionCampaign ────────────────────────────────────────────────────────


def create_campaign(db: Session, data: dict[str, Any]) -> ExecutionCampaign:
    row = ExecutionCampaign(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_campaign(db: Session, campaign_id: int, project_id: int) -> ExecutionCampaign | None:
    return db.scalar(
        select(ExecutionCampaign).where(
            ExecutionCampaign.id == campaign_id, ExecutionCampaign.project_id == project_id
        )
    )


def update_campaign(
    db: Session, row: ExecutionCampaign, data: dict[str, Any]
) -> ExecutionCampaign:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def list_campaigns(
    db: Session, mission_id: int, limit: int = 50
) -> list[ExecutionCampaign]:
    return list(
        db.scalars(
            select(ExecutionCampaign)
            .where(ExecutionCampaign.mission_id == mission_id)
            .order_by(ExecutionCampaign.id.desc())
            .limit(limit)
        ).all()
    )


def add_campaign_scenario(db: Session, data: dict[str, Any]) -> CampaignScenario:
    row = CampaignScenario(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_campaign_scenarios(
    db: Session, campaign_id: int
) -> list[CampaignScenario]:
    return list(
        db.scalars(
            select(CampaignScenario)
            .where(CampaignScenario.campaign_id == campaign_id)
            .order_by(CampaignScenario.id.asc())
        ).all()
    )


def update_campaign_scenario(
    db: Session, row: CampaignScenario, data: dict[str, Any]
) -> CampaignScenario:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── RunProfile ───────────────────────────────────────────────────────────────


def create_run_profile(db: Session, data: dict[str, Any]) -> RunProfile:
    row = RunProfile(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_run_profile(db: Session, profile_id: int, project_id: int) -> RunProfile | None:
    return db.scalar(
        select(RunProfile).where(
            RunProfile.id == profile_id, RunProfile.project_id == project_id
        )
    )


def list_run_profiles(db: Session, project_id: int) -> list[RunProfile]:
    return list(
        db.scalars(
            select(RunProfile)
            .where(RunProfile.project_id == project_id)
            .order_by(RunProfile.id.desc())
        ).all()
    )


# ── Trigger ──────────────────────────────────────────────────────────────────


def create_trigger(db: Session, data: dict[str, Any]) -> Trigger:
    row = Trigger(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_triggers(db: Session, project_id: int) -> list[Trigger]:
    return list(
        db.scalars(
            select(Trigger)
            .where(Trigger.project_id == project_id)
            .order_by(Trigger.id.desc())
        ).all()
    )


def get_trigger(db: Session, trigger_id: int, project_id: int) -> Trigger | None:
    return db.scalar(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.project_id == project_id)
    )


def update_trigger(db: Session, row: Trigger, data: dict[str, Any]) -> Trigger:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── Quality Gate ─────────────────────────────────────────────────────────────


def create_gate_policy(db: Session, data: dict[str, Any]) -> QualityGatePolicy:
    row = QualityGatePolicy(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_active_gate_policy(
    db: Session, project_id: int
) -> QualityGatePolicy | None:
    return db.scalar(
        select(QualityGatePolicy)
        .where(QualityGatePolicy.project_id == project_id, QualityGatePolicy.status == "ACTIVE")
        .order_by(QualityGatePolicy.id.desc())
        .limit(1)
    )


def create_gate_result(db: Session, data: dict[str, Any]) -> QualityGateResultRecord:
    row = QualityGateResultRecord(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_gate_result(
    db: Session, row: QualityGateResultRecord, data: dict[str, Any]
) -> QualityGateResultRecord:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def get_gate_result(
    db: Session, result_id: int, mission_id: int
) -> QualityGateResultRecord | None:
    return db.scalar(
        select(QualityGateResultRecord).where(
            QualityGateResultRecord.id == result_id,
            QualityGateResultRecord.mission_id == mission_id,
        )
    )


def list_gate_results(
    db: Session, mission_id: int, limit: int = 50
) -> list[QualityGateResultRecord]:
    return list(
        db.scalars(
            select(QualityGateResultRecord)
            .where(QualityGateResultRecord.mission_id == mission_id)
            .order_by(QualityGateResultRecord.id.desc())
            .limit(limit)
        ).all()
    )
