"""AITDE V3 AI governance service tests (V30-080..V30-084)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import mission as mission_pkg  # noqa: F401  registers models
from app.core.exceptions import APIException
from app.modules.aitde.ai_ops import service as ai_ops
from app.modules.aitde.ai_ops.prompts import PromptLoader
from app.modules.aitde.common.enums import AIOperationStatus


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


def test_lifecycle_transitions(db):
    op = ai_ops.create_operation(db, 1, 1, "scope:analyze", user_id=9)
    assert op.status == AIOperationStatus.QUEUED.value
    ai_ops.mark_running(db, op)
    assert op.status == AIOperationStatus.RUNNING.value
    ai_ops.mark_succeeded(db, op, result_ref={"items": 2}, duration_ms=100)
    assert op.status == AIOperationStatus.SUCCEEDED.value
    assert op.duration_ms == 100


def test_get_missing_operation_raises_not_found(db):
    with pytest.raises(APIException) as exc:
        ai_ops.get_operation(db, 9999)
    assert exc.value.http_status == 404


def test_source_ref_validator_flags_invalid(db):
    assert ai_ops.validate_source_refs(db, [{"artifact_id": 0, "fragment_id": 0}]) == []
    invalid = ai_ops.validate_source_refs(db, [{"artifact_id": 9999}])
    assert invalid == ["artifact_id=9999"]


def test_prompt_loader_returns_version(db):
    pv = PromptLoader().load("scope_analysis_v1")
    assert pv.name == "scope_analysis_v1"
    assert ":" in pv.version
    assert len(pv.content) > 0


def test_prompt_loader_serves_ambiguity_intent_v1(db):
    """v331-gap C5 (V30-041)：ambiguity_intent_v1 prompt 必须存在且可加载。"""
    pv = PromptLoader().load("ambiguity_intent_v1")
    assert pv.name == "ambiguity_intent_v1"
    assert ":" in pv.version
    # 输出契约锚点：歧义候选与意图候选的关键字段必须在 prompt 中声明
    assert "ambiguity_key" in pv.content
    assert "intent_key" in pv.content
    assert "candidate_options" in pv.content
    assert "required_outcomes" in pv.content


def test_repair_retry_allows_one_retry(db):
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("transient")
        return "ok"

    assert ai_ops.repair_retry(boom) == "ok"
    assert calls["n"] == 2


# ── v331-remediation-2 B2: AI Debug Drawer list endpoint ────────────────────


def test_list_operations_filters_by_mission_and_project(db):
    from app.modules.aitde.ai_ops import models as ai_models  # noqa: F401 registers tables

    ai_ops.create_operation(db, project_id=1, mission_id=1, operation_type="scope:analyze", user_id=9)
    ai_ops.create_operation(db, project_id=1, mission_id=1, operation_type="contract:generate", user_id=9)
    ai_ops.create_operation(db, project_id=1, mission_id=2, operation_type="scope:analyze", user_id=9)
    ai_ops.create_operation(db, project_id=2, mission_id=1, operation_type="scope:analyze", user_id=9)

    items = ai_ops.list_operations(db, mission_id=1, project_id=1)
    assert [i.operation_type for i in items] == ["contract:generate", "scope:analyze"]


def test_list_operations_endpoint_requires_debug_permission(db_session, client, auth_headers):
    """mission:ai_view_debug 门控：无权限 403，超级权限 200。"""
    from app.core import config
    config.settings.aitde_v3_enabled = True
    from app.core import deps
    from app.core.deps import CurrentUser
    from app.core.exceptions import APIException
    from app.models.user import User

    checker = deps._require_permission_only("mission:ai_view_debug")
    tester = CurrentUser(
        user=User(id=2, username="t", password="x"),
        permissions=["mission:detail"],
        project_id=1,
        system_permissions=None,
    )
    with __import__("pytest").raises(APIException) as exc:
        checker(tester)
    assert exc.value.http_status == 403

    resp = client.get("/api/v2/ai-operations?mission_id=1", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"] == []
