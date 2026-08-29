"""AITDE V3 Scenario service tests (V30-060..V30-071)."""

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
from app.modules.aitde.contract.schemas import (
    ContractFreezeRequest,
    ContractGenerateRequest,
)
from app.modules.aitde.scenario import service as scenario_service
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


def _to_frozen_contract(db, mission_id):
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
    res = contract_service.generate(db, mission_id, 1, 9, ContractGenerateRequest())
    contract_service.freeze(
        db,
        res["contract_id"],
        mission_id,
        1,
        9,
        ContractFreezeRequest(expected_version=1, confirm=True),
    )
    return res


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


def test_generate_requires_frozen_contract(db):
    _ready(db)
    # no frozen contract yet -> create a draft version then attempt generate
    with pytest.raises(APIException) as exc:
        scenario_service.generate(db, 1, 1, 9)
    assert exc.value.http_status in (404, 409)


def test_generate_and_list_and_projection(db):
    m = _ready(db)
    res = _to_frozen_contract(db, m.id)
    gen = scenario_service.generate(db, res["version_id"], 1, 9)
    assert gen["scenario_count"] >= 1

    lst = scenario_service.list_scenarios(db, m.id, 1)
    assert len(lst) >= 1
    detail = scenario_service.get_scenario(db, lst[0]["id"], 1)
    assert "oracles" in detail
    assert len(detail["oracles"]) >= 1

    projection = scenario_service.functional_projection(db, lst[0]["id"], 1)
    assert projection.priority in ("P0", "P1", "P2", "P3")
    assert len(projection.steps) >= 1


def test_generate_requires_frozen_contract_draft(db):
    m = _ready(db)
    # build scope + intent (so contract can generate) but do NOT freeze
    scope_service.analyze_scope(db, m.id, 1, 9)
    rows, _ = scope_service.list_scope(db, m.id)
    scope_service.review_scope(
        db,
        m.id,
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
    ambiguity_service.analyze(db, m.id, 1, 9)
    for i in ambiguity_service.list_intents(db, m.id):
        ambiguity_service.review_intent(
            db, i.id, 1, 9, IntentReviewRequest(action="approve")
        )
    res = contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())
    with pytest.raises(APIException) as exc:
        scenario_service.generate(db, res["version_id"], 1, 9)
    assert exc.value.http_status == 409
