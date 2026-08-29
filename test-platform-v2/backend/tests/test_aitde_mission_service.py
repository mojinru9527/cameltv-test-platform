"""AITDE V3 Mission service lifecycle tests (V30-010/V30-012).

Uses an in-memory SQLite DB (StaticPool) so the run is isolated from any real
platform database.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import mission as mission_pkg  # noqa: F401  registers Mission
from app.core.exceptions import APIException
from app.modules.aitde.common.enums import MissionStatus
from app.modules.aitde.mission import service


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


def _create(db, **overrides):
    data = {"title": "会员中心 V3.6"}
    data.update(overrides)
    return service.create_mission(db, data, project_id=1, user_id=9)


def test_create_sets_expected_defaults(db):
    mission = _create(db)
    assert mission.mission_key == "M-1-0001"
    assert mission.title == "会员中心 V3.6"
    assert mission.status == MissionStatus.DRAFT.value
    assert mission.mission_type == "VERSION"


def test_list_scoped_to_project(db):
    _create(db, title="A")
    _create(db, title="B")
    # a different project's mission must not leak into project 1's list
    service.create_mission(db, {"title": "C"}, project_id=2, user_id=4)
    items, total = service.list_missions(db, 1)
    assert total == 2
    assert all(m.mission_key.startswith("M-1-") for m in items)


def test_rejects_illegal_status_transition(db):
    mission = _create(db)
    with pytest.raises(APIException) as exc:
        service.update_mission(
            db, mission.id, 1, {"status": MissionStatus.CONTRACT_FROZEN.value}
        )
    assert exc.value.http_status == 400
    assert "非法状态迁移" in exc.value.msg


def test_allows_legal_status_transition(db):
    mission = _create(db)
    updated = service.update_mission(
        db, mission.id, 1, {"status": MissionStatus.SOURCE_READY.value}
    )
    assert updated.status == MissionStatus.SOURCE_READY.value


def test_archive_marks_archived_and_timestamp(db):
    mission = _create(db)
    archived = service.archive_mission(db, mission.id, 1)
    assert archived.status == MissionStatus.ARCHIVED.value
    assert archived.archived_at is not None


def test_get_unknown_mission_raises_not_found(db):
    with pytest.raises(APIException) as exc:
        service.get_mission(db, 9999, 1)
    assert exc.value.http_status == 404
