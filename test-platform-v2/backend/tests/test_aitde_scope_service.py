"""AITDE V3 Scope service tests (V30-030..V30-039)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import mission as mission_pkg  # noqa: F401  registers models
from app.core.exceptions import APIException
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.sources import service as source_service
from app.modules.aitde.sources.schemas import SourceArtifactCreate
from app.modules.aitde.scope import service as scope_service
from app.modules.aitde.scope.schemas import ScopeBulkReviewRequest, ScopeReviewItem
from app.modules.aitde.common.enums import ReviewStatus, ScopeDecision


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


def _mission(db, title="V3.6"):
    return mission_service.create_mission(db, {"title": title}, project_id=1, user_id=9)


def _with_parsed_source(db, mission_id):
    src = source_service.attach_source(
        db,
        SourceArtifactCreate(
            source_type="MANUAL_NOTE", name="补", content="会员续费后立即恢复权益。"
        ),
        mission_id,
        1,
        9,
    )
    return src


def test_analyze_requires_parsed_source(db):
    m = _mission(db)
    with pytest.raises(APIException) as exc:
        scope_service.analyze_scope(db, m.id, 1, 9)
    assert exc.value.http_status == 400


def test_analyze_creates_proposed_items(db):
    m = _mission(db)
    _with_parsed_source(db, m.id)
    items = scope_service.analyze_scope(db, m.id, 1, 9)
    assert len(items) >= 1
    assert items[0].review_status == ReviewStatus.PROPOSED.value
    assert 0 <= items[0].ai_confidence <= 1


def test_summary_progress_after_review(db):
    m = _mission(db)
    _with_parsed_source(db, m.id)
    scope_service.analyze_scope(db, m.id, 1, 9)
    rows, summary = scope_service.list_scope(db, m.id)
    assert summary.total == len(rows)
    assert summary.review_progress == 0

    scope_service.review_scope(
        db,
        m.id,
        1,
        9,
        ScopeBulkReviewRequest(
            items=[
                ScopeReviewItem(
                    scope_key=rows[0].scope_key,
                    decision=ScopeDecision.INCLUDE,
                    action="approve",
                )
            ]
        ),
    )
    _, summary2 = scope_service.list_scope(db, m.id)
    assert summary2.approved == 1
    assert summary2.review_progress == 1.0


def test_complete_policy_empty_raises(db):
    m = _mission(db)
    with pytest.raises(APIException) as exc:
        scope_service.complete_policy(db, m.id)
    assert exc.value.http_status == 400
