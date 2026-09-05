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


def _complete_scope_and_intent(db, mission_id, decision=ScopeDecision.INCLUDE):
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
                    decision=decision,
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


# --- Batch 230 S1 / DEF-20260905-001 -------------------------------------


def test_get_current_returns_parsed_snapshot(db):
    """契约页需要读到规则内容；此前 `_version_to_dict` 丢弃 snapshot_json。"""
    m = _ready(db)
    _complete_scope_and_intent(db, m.id)
    contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())

    current = contract_service.get_current(db, m.id)
    snapshot = current["version"]["snapshot"]

    assert isinstance(snapshot, dict)
    assert snapshot["mission_id"] == m.id
    assert len(snapshot["rules"]) > 0
    assert snapshot["rules"][0]["title"]


def test_get_current_endpoint_treats_missing_contract_as_business_empty_state(
    client, db_session, admin_user, auth_headers, monkeypatch,
):
    """首次进入契约页是正常空态，不应产生浏览器资源 404。"""
    from app.core import config

    monkeypatch.setattr(config.settings, "aitde_v3_enabled", True)
    mission = mission_service.create_mission(
        db_session,
        {"title": "尚未生成契约"},
        project_id=1,
        user_id=admin_user.id,
    )

    response = client.get(
        f"/api/v2/missions/{mission.id}/contract",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "code": 404,
        "msg": "Contract 尚未生成",
        "data": None,
    }


def test_list_versions_returns_parsed_snapshot(db):
    m = _ready(db)
    _complete_scope_and_intent(db, m.id)
    result = contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())

    versions = contract_service.list_versions(db, result["contract_id"])

    assert len(versions) == 1
    assert versions[0]["snapshot"]["schema_version"] == "1.0"


def test_freeze_rejects_empty_rules_snapshot(db):
    """全部 EXCLUDE → review_progress 仍为 1.0 → 前置校验放行 → 零规则空壳。

    空壳契约一旦被冻结，Mission 会带着「已有标准答案」的假状态推进（P1-3）。
    必须是 400 而非 409：前端把 409 绑定为乐观锁冲突并提示「请刷新」。
    """
    m = _ready(db)
    _complete_scope_and_intent(db, m.id, decision=ScopeDecision.EXCLUDE)
    result = contract_service.generate(db, m.id, 1, 9, ContractGenerateRequest())

    snapshot = contract_service.get_current(db, m.id)["version"]["snapshot"]
    assert snapshot["rules"] == []

    with pytest.raises(APIException) as exc:
        contract_service.freeze(
            db,
            result["contract_id"],
            m.id,
            1,
            9,
            ContractFreezeRequest(expected_version=1, confirm=True),
        )

    assert exc.value.http_status == 400
    assert "CONTRACT_FREEZE_EMPTY" in exc.value.msg

    # 拦截后 Mission 不得被推进到 CONTRACT_FROZEN
    db.refresh(m)
    assert m.status != "CONTRACT_FROZEN"


def test_parse_snapshot_tolerates_malformed_json():
    """snapshot_json 是 Text 列，历史数据可能畸形（系统边界，防御解析）。"""
    assert contract_service._parse_snapshot(None) is None
    assert contract_service._parse_snapshot("") is None
    assert contract_service._parse_snapshot("{not json") is None
    assert contract_service._parse_snapshot("{}") is None
    assert contract_service._parse_snapshot('{"mission_id": 7}')['rules'] == []
