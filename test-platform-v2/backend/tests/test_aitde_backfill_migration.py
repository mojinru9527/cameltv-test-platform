"""AITDE V3 legacy backfill migration tests (V30-110, M4)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
import app.models  # noqa: F401  registers VersionMission + everything
import app.modules.aitde  # noqa: F401  registers Mission / sources
from app.models.version_mission import VersionMission
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.sources.models import MissionSourceLink
from app.modules.aitde.common.enums import MissionStatus
from scripts import migrate_version_missions_to_v3 as migrator


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _legacy(db, **overrides):
    row = VersionMission(
        project_id=1,
        mission_key="M-LEGACY-01",
        title="会员中心 V3.6",
        version="v3.6",
        qa_owner_id=9,
        created_by=7,
        environment_id=3,
        requirement_doc_id=101,
        status="draft",
        **overrides,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_dry_run_does_not_write(db):
    _legacy(db)
    result = migrator.migrate(db, dry_run=True)
    assert result["planned"] == 1
    assert result["skipped"] == 0
    # nothing written on dry-run
    assert db.scalar(select(Mission)) is None


def test_migrate_creates_mission_conservatively(db):
    row = _legacy(db)
    result = migrator.migrate(db, dry_run=False)
    assert result["planned"] == 1
    mission = db.scalar(
        select(Mission).where(Mission.legacy_version_mission_id == row.id)
    )
    assert mission is not None
    assert mission.title == "会员中心 V3.6"
    assert mission.version_label == "v3.6"
    assert mission.default_environment_id == 3
    # conservative: never auto-freeze/ready
    assert mission.status in (
        MissionStatus.DRAFT.value,
        MissionStatus.SOURCE_READY.value,
    )
    # requirement source link created
    assert db.scalar(select(MissionSourceLink)) is not None


def test_migrate_is_idempotent(db):
    _legacy(db)
    migrator.migrate(db, dry_run=False)
    result = migrator.migrate(db, dry_run=False)
    assert result["skipped"] == 1
    assert result["planned"] == 0
