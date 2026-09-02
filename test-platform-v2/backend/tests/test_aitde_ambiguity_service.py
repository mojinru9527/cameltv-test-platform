"""AITDE V3 Ambiguity / Intent service tests (V30-040..V30-047)."""
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
from app.modules.aitde.scope import ambiguity_service as ambiguity_service
from app.modules.aitde.common.enums import ScopeDecision
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityResolveRequest,
    IntentReviewRequest,
)
from app.modules.aitde.scope.schemas import ScopeBulkReviewRequest, ScopeReviewItem


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


def _ready_mission(db, content="会员续费后立即恢复权益。"):
    m = mission_service.create_mission(db, {"title": "V3.6"}, project_id=1, user_id=9)
    source_service.attach_source(
        db,
        SourceArtifactCreate(source_type="MANUAL_NOTE", name="补", content=content),
        m.id,
        1,
        9,
    )
    scope_service.analyze_scope(db, m.id, 1, 9)
    return m


def test_analyze_creates_intents_without_fake_ambiguities(db):
    # Batch 207: a confident INCLUDE scope item is not ambiguous; the
    # deterministic baseline must not manufacture a question per item.
    m = _ready_mission(db)
    counts = ambiguity_service.analyze(db, m.id, 1, 9)
    assert counts["ambiguity_count"] == 0
    assert counts["intent_count"] >= 1
    assert len(ambiguity_service.list_ambiguities(db, m.id)) == 0
    assert len(ambiguity_service.list_intents(db, m.id)) >= 1


def _exclude_one_scope(db, m):
    rows, _ = scope_service.list_scope(db, m.id)
    scope_service.review_scope(
        db,
        m.id,
        1,
        9,
        ScopeBulkReviewRequest(
            items=[
                ScopeReviewItem(
                    scope_key=rows[0].scope_key,
                    decision=ScopeDecision.EXCLUDE,
                    action="approve",
                )
            ]
        ),
    )


def test_analyze_flags_excluded_scope_as_ambiguity(db):
    m = _ready_mission(db)
    _exclude_one_scope(db, m)
    counts = ambiguity_service.analyze(db, m.id, 1, 9)
    assert counts["ambiguity_count"] >= 1


def test_resolve_ambiguity_marks_resolved(db):
    m = _ready_mission(db)
    _exclude_one_scope(db, m)
    ambiguity_service.analyze(db, m.id, 1, 9)
    ambiguity = ambiguity_service.list_ambiguities(db, m.id)[0]
    resolved = ambiguity_service.resolve_ambiguity(
        db, ambiguity.id, 1, 9, AmbiguityResolveRequest(selected_option_key="allow")
    )
    assert resolved.status == "RESOLVED"


def test_review_intent_approves(db):
    m = _ready_mission(db)
    ambiguity_service.analyze(db, m.id, 1, 9)
    intent = ambiguity_service.list_intents(db, m.id)[0]
    reviewed = ambiguity_service.review_intent(
        db, intent.id, 1, 9, IntentReviewRequest(action="approve")
    )
    assert reviewed.review_status == "APPROVED"


def test_resolve_missing_ambiguity_raises_not_found(db):
    _ready_mission(db)
    with pytest.raises(APIException) as exc:
        ambiguity_service.resolve_ambiguity(
            db, 9999, 1, 9, AmbiguityResolveRequest(selected_option_key="allow")
        )
    assert exc.value.http_status == 404
