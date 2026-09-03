"""AITDE V3 Source normalization service tests (V30-020..V30-025)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import mission as mission_pkg  # noqa: F401  registers models
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.sources import service as source_service
from app.modules.aitde.sources.schemas import SourceArtifactCreate
from app.core.exceptions import APIException


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


def _mission(db):
    return mission_service.create_mission(
        db, {"title": "V3.6"}, project_id=1, user_id=9
    )


def test_manual_note_parses_immediately(db):
    m = _mission(db)
    note = source_service.attach_source(
        db,
        SourceArtifactCreate(
            source_type="MANUAL_NOTE",
            name="补充",
            content="过期会员续费后立即恢复权益。",
        ),
        m.id,
        1,
        9,
    )
    assert note.parse_status == "PARSED"
    frags = source_service.fragments(db, note.id, 1)
    assert len(frags) == 1


def test_openapi_attaches_pending_then_parses(db):
    m = _mission(db)
    oas = source_service.attach_source(
        db,
        SourceArtifactCreate(source_type="OPENAPI", uri="https://x/openapi.json"),
        m.id,
        1,
        9,
    )
    assert oas.parse_status == "PENDING"
    result = source_service.parse_source(db, oas.id, 1)
    assert result.parse_status == "PARSED"
    assert result.fragment_count >= 1


def test_list_sources_scoped_to_mission(db):
    m = _mission(db)
    source_service.attach_source(
        db,
        SourceArtifactCreate(source_type="MANUAL_NOTE", name="n1", content="a"),
        m.id,
        1,
        9,
    )
    source_service.attach_source(
        db,
        SourceArtifactCreate(source_type="MANUAL_NOTE", name="n2", content="b"),
        m.id,
        1,
        9,
    )
    assert len(source_service.list_sources(db, m.id)) == 2


def test_attach_to_missing_mission_raises_not_found(db):
    with pytest.raises(APIException) as exc:
        source_service.attach_source(
            db,
            SourceArtifactCreate(source_type="MANUAL_NOTE", name="x", content="y"),
            9999,
            1,
            9,
        )
    assert exc.value.http_status == 404


def test_source_list_endpoints_return_array_envelopes(
    client, db_session, admin_user, auth_headers, monkeypatch,
):
    """List endpoints must serialize their list payloads instead of raising HTTP 500."""
    from app.core import config

    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    mission = mission_service.create_mission(
        db_session,
        {"title": "体育平台 16.0.0"},
        project_id=1,
        user_id=admin_user.id,
    )
    source = source_service.attach_source(
        db_session,
        SourceArtifactCreate(
            source_type="MANUAL_NOTE",
            name="体育需求",
            content="篮球与足球数据必须按体育项目隔离。",
        ),
        mission.id,
        1,
        admin_user.id,
    )

    sources_response = client.get(
        f"/api/v2/missions/{mission.id}/sources", headers=auth_headers
    )
    fragments_response = client.get(
        f"/api/v2/missions/{mission.id}/sources/{source.id}/fragments",
        headers=auth_headers,
    )

    assert sources_response.status_code == 200
    assert sources_response.json()["code"] == 0
    assert [item["id"] for item in sources_response.json()["data"]] == [source.id]
    assert fragments_response.status_code == 200
    assert fragments_response.json()["code"] == 0
    assert fragments_response.json()["data"][0]["text"] == "篮球与足球数据必须按体育项目隔离。"
