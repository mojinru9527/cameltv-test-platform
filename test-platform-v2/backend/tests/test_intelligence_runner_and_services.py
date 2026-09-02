"""Batch 207 — intelligence runner instrumentation + service provenance.

AI-mode calls must write ai_operations (SUCCEEDED/FAILED) and stamp
created_by_type=AI; deterministic calls write nothing and stamp
DETERMINISTIC. A failed AI call degrades to the deterministic baseline but
keeps the FAILED operation for the drawer.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde import mission as mission_pkg  # noqa: F401  registers models
from app.modules.aitde.ai_ops.models import AIOperationRecord
from app.modules.aitde.common.enums import AIOperationStatus
from app.modules.aitde.intelligence import provider as provider_mod
from app.modules.aitde.intelligence import runner
from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMError
from app.modules.aitde.intelligence.provider import (
    DeterministicScopeProvider,
    ScopeAnalysisCandidate,
    ScopeAnalysisOutput,
    ScopeContext,
)
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.scope import service as scope_service
from app.modules.aitde.sources import service as source_service
from app.modules.aitde.sources.schemas import SourceArtifactCreate

_CTX = ScopeContext(mission_id=3, fragments=[(1, 2, "标题", "正文内容")])


def _candidate() -> ScopeAnalysisCandidate:
    return ScopeAnalysisCandidate.model_validate(
        {
            "scope_key": "scope-1-2",
            "scope_type": "BUSINESS_FLOW",
            "name": "会员续费",
            "decision": "INCLUDE",
            "test_depth": "FULL",
            "risk_level": "P2",
            "reason": "续费后恢复权益",
            "confidence": 0.9,
            "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
        }
    )


class _FakeAIProvider:
    mode = "ai"
    created_by_type = "AI"

    def __init__(self, fail: bool = False):
        self.fail = fail

    def analyze_scope(self, context):
        if self.fail:
            raise IntelligenceLLMError("boom")
        return ScopeAnalysisOutput(
            schema_version="1.0", mission_id=context.mission_id, items=[_candidate()]
        )


def _analyze_via(prov):
    return prov.analyze_scope(_CTX)


def test_run_intelligence_ai_success_writes_operation(db_session, monkeypatch):
    monkeypatch.setattr(
        provider_mod, "build_intelligence_provider", lambda db, pid: _FakeAIProvider()
    )
    result, op_id, actor = runner.run_intelligence(
        db_session, project_id=1, mission_id=3, operation_type="scope:analyze",
        fn=_analyze_via,
    )
    assert actor == "AI"
    assert op_id is not None
    assert len(result.items) == 1
    row = db_session.get(AIOperationRecord, op_id)
    assert row.status == AIOperationStatus.SUCCEEDED.value
    assert row.operation_type == "scope:analyze"
    assert row.mission_id == 3


def test_run_intelligence_ai_failure_records_failed_and_degrades(db_session, monkeypatch):
    monkeypatch.setattr(
        provider_mod, "build_intelligence_provider", lambda db, pid: _FakeAIProvider(fail=True)
    )
    result, op_id, actor = runner.run_intelligence(
        db_session, project_id=1, mission_id=3, operation_type="scope:analyze",
        fn=_analyze_via,
    )
    assert actor == "DETERMINISTIC"
    assert op_id is not None
    assert len(result.items) == 1
    row = db_session.get(AIOperationRecord, op_id)
    assert row.status == AIOperationStatus.FAILED.value
    assert row.error_code == "AI_CALL_FAILED"


def test_run_intelligence_deterministic_writes_nothing(db_session, monkeypatch):
    monkeypatch.setattr(
        provider_mod, "build_intelligence_provider", lambda db, pid: DeterministicScopeProvider()
    )
    result, op_id, actor = runner.run_intelligence(
        db_session, project_id=1, mission_id=3, operation_type="scope:analyze",
        fn=_analyze_via,
    )
    assert actor == "DETERMINISTIC"
    assert op_id is None
    count = db_session.query(AIOperationRecord).filter_by(mission_id=3).count()
    assert count == 0


def _mission_with_parsed_source(db):
    m = mission_service.create_mission(db, {"title": "V207"}, project_id=1, user_id=9)
    source_service.attach_source(
        db,
        SourceArtifactCreate(
            source_type="MANUAL_NOTE", name="补", content="会员续费后恢复权益"
        ),
        m.id,
        1,
        9,
    )
    return m


def test_scope_service_default_is_deterministic_provenance(db_session):
    m = _mission_with_parsed_source(db_session)
    items = scope_service.analyze_scope(db_session, m.id, 1, 9)
    assert items[0].created_by_type == "DETERMINISTIC"
    count = db_session.query(AIOperationRecord).filter_by(mission_id=m.id).count()
    assert count == 0


def test_scope_service_ai_mode_stamps_ai_and_operation(db_session, monkeypatch):
    monkeypatch.setattr(
        provider_mod, "build_intelligence_provider", lambda db, pid: _FakeAIProvider()
    )
    m = _mission_with_parsed_source(db_session)
    items = scope_service.analyze_scope(db_session, m.id, 1, 9)
    assert items[0].created_by_type == "AI"
    count = db_session.query(AIOperationRecord).filter_by(mission_id=m.id).count()
    assert count == 1


def test_scope_service_requires_parsed_source_still(db_session):
    m = mission_service.create_mission(db_session, {"title": "V207"}, project_id=1, user_id=9)
    with pytest.raises(APIException) as exc:
        scope_service.analyze_scope(db_session, m.id, 1, 9)
    assert exc.value.http_status == 400
