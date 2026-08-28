"""AITDE V3 Contract service tests (V30-050..V30-059)."""

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
from app.modules.aitde.scope.schemas import ScopeBulkReviewRequest, ScopeReviewItem
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityResolveRequest,
    IntentReviewRequest,
)
from app.modules.aitde.contract import service as contract_service
from app.modules.aitde.contract import repository
from app.modules.aitde.contract.schemas import (
    ContractFreezeRequest,
    ContractGenerateRequest,
)
from app.modules.aitde.common.enums import ScopeDecision


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


def _ready(db):
    m = mission_service.create_mission(db, {"title": "V3.6"}, project_id=1, user_id=9)
    source_service.attach_source(
        db,
        SourceArtifactCreate(
            source_type="MANUAL_NOTE", name="补", content="会员续费后恢复权益。"
        ),
        m.id,
        1,
        9,
    )
    return m


def _complete_scope_and_intent(db, mission_id):
    scope_service.analyze_scope(db, mission_id, 1, 9)
    rows, _ = scope_service.list_scope(db, mission_id)
    scope_service.review_scope(
        db,
        mission_id,
        1,
        9,
        ScopeBulkReviewRequest(
            items=[
                ScopeReviewItem(
                    scope_key=r.scope_key,
                    decision=ScopeDecision.INCLUDE,
                    action="approve",
                )
                for r in rows
            ]
        ),
    )
    ambiguity_service.analyze(db, mission_id, 1, 9)
    for a in ambiguity_service.list_ambiguities(db, mission_id):
        ambiguity_service.resolve_ambiguity(
            db, a.id, 1, 9, AmbiguityResolveRequest(selected_option_key="allow")
        )
    for i in ambiguity_service.list_intents(db, mission_id):
        ambiguity_service.review_intent(
            db, i.id, 1, 9, IntentReviewRequest(action="approve")
        )


def test_generate_requires_scope_complete(db):
    m = _ready(db)
    with pytest.raises(APIException) as exc:
        contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())
    assert exc.value.http_status == 409


def test_generate_and_freeze_flow(db):
    m = _ready(db)
    _complete_scope_and_intent(db, m.id)
    result = contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())
    assert result["version_no"] == 1

    current = contract_service.get_current(db, m.id)
    assert current["version"]["status"] == "DRAFT"

    frozen = contract_service.freeze(
        db,
        current["contract_id"],
        m.id,
        1,
        9,
        ContractFreezeRequest(expected_version=1, confirm=True),
    )
    assert frozen["status"] == "FROZEN"


def test_frozen_version_is_immutable(db):
    m = _ready(db)
    _complete_scope_and_intent(db, m.id)
    result = contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())
    contract_service.freeze(
        db,
        result["contract_id"],
        m.id,
        1,
        9,
        ContractFreezeRequest(expected_version=1, confirm=True),
    )
    version = repository.get_version_by_id(db, result["version_id"])
    with pytest.raises(APIException) as exc:
        repository.ensure_mutable(version)
    assert exc.value.http_status == 409
