"""Batch 248 — 本地 AI Agent 闭环：Job 生产端 / Agent 凭据 / stale 回收 / 上报。"""
from __future__ import annotations

from datetime import timedelta

from app.models.ai_job import AiResult
from app.services import ai_agent_service
from app.services.ai_job_dispatch import dispatch_requirement_job, local_agent_mode
from app.core.exceptions import APIException

import pytest


def test_register_agent_issues_verifiable_token(db_session) -> None:
    agent, plain = ai_agent_service.register_agent(db_session, "agent-a", 7, ["extract"])
    assert agent.agent_id == "agent-a"
    assert plain and plain.startswith("agt_")

    token = ai_agent_service.verify_agent_token(db_session, plain)
    assert token is not None
    assert token.agent_id == "agent-a"
    assert token.project_id == 7

    assert ai_agent_service.verify_agent_token(db_session, "agt_bogus") is None


def test_revoked_agent_token_is_rejected(db_session) -> None:
    _agent, plain = ai_agent_service.register_agent(db_session, "agent-rev", 7, ["extract"])
    token = ai_agent_service.verify_agent_token(db_session, plain)
    assert token is not None
    assert ai_agent_service.revoke_agent_token(db_session, token.id, 7) is True
    assert ai_agent_service.verify_agent_token(db_session, plain) is None
    # 跨项目吊销必须失败
    _a2, plain2 = ai_agent_service.register_agent(db_session, "agent-rev2", 8, ["extract"])
    token2 = ai_agent_service.verify_agent_token(db_session, plain2)
    assert ai_agent_service.revoke_agent_token(db_session, token2.id, 999) is False


def test_job_creation_and_project_isolation(db_session) -> None:
    job = ai_agent_service.create_job(
        db_session, project_id=7, job_type="extract", payload={"document_id": 1}
    )
    assert job.status == "pending"
    assert job.capability == "extract"

    rows, total = ai_agent_service.list_jobs(db_session, project_id=7)
    assert total == 1 and rows[0].id == job.id
    assert ai_agent_service.list_jobs(db_session, project_id=8)[1] == 0
    assert ai_agent_service.get_job(db_session, project_id=8, job_id=job.id) is None
    assert ai_agent_service.get_job(db_session, project_id=7, job_id=job.id) is not None


def test_claim_respects_capability_and_project(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-cap", 7, ["extract"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="generate", payload={})
    assert ai_agent_service.claim_job(db_session, "agent-cap", ["extract"]) is None

    job = ai_agent_service.claim_job(db_session, "agent-cap", ["generate"])
    assert job is not None and job.status == "running"

    # 其它项目的 Agent 不能认领本项目任务
    ai_agent_service.register_agent(db_session, "agent-other", 99, ["generate"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="generate", payload={})
    assert ai_agent_service.claim_job(db_session, "agent-other", ["generate"], project_id=99) is None


def test_stale_running_job_can_be_reclaimed(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-lost", 7, ["extract"], issue_token=False)
    job = ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})
    claimed = ai_agent_service.claim_job(db_session, "agent-lost", ["extract"])
    assert claimed is not None

    # 心跳停留在 1 小时前 → 视为失联
    claimed.heartbeat_at = claimed.heartbeat_at - timedelta(hours=1)
    claimed.locked_at = claimed.heartbeat_at
    db_session.commit()

    ai_agent_service.register_agent(db_session, "agent-alive", 7, ["extract"], issue_token=False)
    reclaimed = ai_agent_service.claim_job(db_session, "agent-alive", ["extract"], project_id=7)
    assert reclaimed is not None and reclaimed.id == job.id
    assert reclaimed.agent_id == "agent-alive"


def test_report_job_records_model_and_result(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-report", 7, ["generate"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="generate", payload={})
    job = ai_agent_service.claim_job(db_session, "agent-report", ["generate"])
    assert job is not None

    reported = ai_agent_service.report_job(
        db_session,
        job.id,
        "agent-report",
        "completed",
        "本地模型产出的用例",
        {"functional_cases": [{"title": "首页冒烟"}]},
        ["local://result.json"],
        "local-chatgpt-5",
        "",
    )
    assert reported is not None and reported.status == "completed"
    assert reported.model_name == "local-chatgpt-5"
    result = db_session.query(AiResult).filter(AiResult.job_id == job.id).one()
    assert "首页冒烟" in result.result_json


def test_report_rejects_unknown_agent(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-ctx", 7, ["extract"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})
    job = ai_agent_service.claim_job(db_session, "agent-ctx", ["extract"])
    assert job is not None
    assert (
        ai_agent_service.report_job(db_session, job.id, "someone-else", "completed", "", {}, [], "", "")
        is None
    )


# ── Slice 2：平台默认不推理，需求域任务改为派发 ──────────────────

def test_platform_inference_is_off_by_default() -> None:
    """平台默认不自己跑 LLM（本地 ChatGPT 客户端负责推理）。"""
    assert local_agent_mode() is True


def test_dispatch_requirement_job_creates_pending_job(db_session) -> None:
    payload = dispatch_requirement_job(
        db_session, document_id=123, job_type="extract", project_id=7, user_id=4
    )
    assert payload["mode"] == "local_agent"
    assert payload["document_id"] == 123
    job = ai_agent_service.get_job(db_session, project_id=7, job_id=payload["job_id"])
    assert job is not None and job.status == "pending" and job.capability == "extract"
    assert "123" in job.input_ref


# ── Slice 3：结果导入 ──────────────────────────────────────────

def test_import_requires_completed_job(db_session) -> None:
    job = ai_agent_service.create_job(db_session, project_id=7, job_type="generate", payload={"document_id": 1})
    with pytest.raises(APIException) as exc:
        ai_agent_service.import_job_result(db_session, project_id=7, job_id=job.id, user_id=4)
    assert exc.value.http_status == 400


def test_import_rejects_extract_type(db_session, monkeypatch) -> None:
    ai_agent_service.register_agent(db_session, "agent-imp", 7, ["extract"], issue_token=False)
    job = ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={"document_id": 1})
    claimed = ai_agent_service.claim_job(db_session, "agent-imp", ["extract"])
    assert claimed is not None
    ai_agent_service.report_job(db_session, job.id, "agent-imp", "completed", "ok", {}, [], "m", "")
    with pytest.raises(APIException) as exc:
        ai_agent_service.import_job_result(db_session, project_id=7, job_id=job.id, user_id=4)
    assert "generate" in str(exc.value.msg)


def test_import_is_idempotent_for_same_job(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-idem", 7, ["generate"], issue_token=False)
    job = ai_agent_service.create_job(db_session, project_id=7, job_type="generate", payload={"document_id": 1})
    ai_agent_service.claim_job(db_session, "agent-idem", ["generate"])
    ai_agent_service.report_job(db_session, job.id, "agent-idem", "completed", "ok", {}, [], "m", "")
    job.imported_at = job.finished_at
    db_session.commit()
    result = ai_agent_service.import_job_result(db_session, project_id=7, job_id=job.id, user_id=4)
    assert result["already_imported"] is True and result["imported"] == 0
