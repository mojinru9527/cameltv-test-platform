"""Batch 208 (C3) — PromptEvaluation real-LLM golden runner tests."""
from __future__ import annotations

import pytest

from app.modules.aitde.ai_closed_loop import service as loop_service
from app.modules.aitde.ai_closed_loop.models import ModelEvaluationRun
from app.services import ai_client
from app.services.ai_client import AiClientUnavailableError

_SAMPLES = [
    {
        "id": "s1",
        "input": "会员续费后应恢复权益",
        "must_include": ["active"],
        "expected": {"status": "active"},
    }
]


def test_run_golden_persists_trusted_run(db, monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: True)
    monkeypatch.setattr(
        ai_client, "chat_completions", lambda *a, **k: {"status": "active"}
    )
    out = loop_service.PromptEvaluationService.run_golden(
        db,
        project_id=1,
        evaluation_suite="suite-a",
        model_ref="m1",
        samples=_SAMPLES,
    )
    assert out["decision"]["passed"] is True
    assert out["decision"]["score"] == pytest.approx(1.0)
    runs = db.query(ModelEvaluationRun).filter_by(evaluation_suite="suite-a").all()
    assert len(runs) == 1
    assert runs[0].metrics_json and '"_trusted":true' in runs[0].metrics_json


def test_run_golden_unconfigured_blocks_without_writing(db, monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: False)
    out = loop_service.PromptEvaluationService.run_golden(
        db,
        project_id=1,
        evaluation_suite="suite-b",
        model_ref="m1",
        samples=_SAMPLES,
    )
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "AI_NOT_CONFIGURED"
    assert db.query(ModelEvaluationRun).filter_by(evaluation_suite="suite-b").count() == 0


def test_run_golden_ai_failure_blocks_without_trusted_run(db, monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: True)

    def _boom(*a, **k):
        raise AiClientUnavailableError("down")

    monkeypatch.setattr(ai_client, "chat_completions", _boom)
    out = loop_service.PromptEvaluationService.run_golden(
        db,
        project_id=1,
        evaluation_suite="suite-c",
        model_ref="m1",
        samples=_SAMPLES,
    )
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "AI_CALL_FAILED"
    assert db.query(ModelEvaluationRun).filter_by(evaluation_suite="suite-c").count() == 0
