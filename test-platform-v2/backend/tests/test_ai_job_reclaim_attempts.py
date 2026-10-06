"""P1-8 — AI Job 回收必须有界：attempt_count + 到顶置为 failed 终态。

原缺陷：`reclaim_stale_jobs` 无条件把心跳超时的 running 任务放回 pending，
而它跑在每一次认领里（`claim_job`），于是「认领 → 超时 → 再认领」会无限循环，
每轮都白烧一次 LLM。
"""
from __future__ import annotations

import logging
from datetime import timedelta

from app.core import config
from app.core.config import Settings
from app.models.ai_job import AiJob
from app.services import ai_agent_service


def _claim(db, agent_id: str = "agent-a", capability: str = "extract"):
    return ai_agent_service.claim_job(db, agent_id, [capability])


def _make_stale(db, job) -> None:
    """把心跳拨回 1 小时前，模拟 Agent 失联。"""
    job.heartbeat_at = ai_agent_service._now() - timedelta(hours=1)
    job.locked_at = job.heartbeat_at
    db.commit()


def test_ai_job_max_attempts_default(monkeypatch) -> None:
    monkeypatch.delenv("AI_JOB_MAX_ATTEMPTS", raising=False)
    assert Settings(_env_file=None).ai_job_max_attempts == 3


def test_claim_increments_attempt_count(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_job_max_attempts", 3)
    ai_agent_service.register_agent(db_session, "agent-a", 7, ["extract"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})

    claimed = _claim(db_session)
    assert claimed is not None
    assert claimed.attempt_count == 1


def test_reclaim_under_cap_requeues_job(db_session, monkeypatch, caplog) -> None:
    monkeypatch.setattr(config.settings, "ai_job_max_attempts", 3)
    ai_agent_service.register_agent(db_session, "agent-a", 7, ["extract"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})
    job = _claim(db_session)
    assert job is not None
    _make_stale(db_session, job)

    with caplog.at_level(logging.INFO, logger="ai.agent"):
        reclaimed = ai_agent_service.reclaim_stale_jobs(db_session)

    assert reclaimed == 1
    assert job.status == "pending"
    assert job.agent_id == ""
    # 每次回收都要留下「第几次 / 上限多少」的可见日志
    assert "attempt 1/3" in caplog.text


def test_reclaim_at_cap_marks_job_terminal_failed(db_session, monkeypatch, caplog) -> None:
    monkeypatch.setattr(config.settings, "ai_job_max_attempts", 2)
    ai_agent_service.register_agent(db_session, "agent-a", 7, ["extract"], issue_token=False)
    ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})

    first = _claim(db_session)
    assert first is not None and first.attempt_count == 1
    _make_stale(db_session, first)
    assert ai_agent_service.reclaim_stale_jobs(db_session) == 1  # 1/2 → 重新入队

    second = _claim(db_session)
    assert second is not None and second.attempt_count == 2
    _make_stale(db_session, second)

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="ai.agent"):
        reclaimed = ai_agent_service.reclaim_stale_jobs(db_session)

    assert reclaimed == 0
    assert second.status == "failed"
    assert second.finished_at is not None
    assert "ai_job_max_attempts=2" in second.error_message
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings and "上限" in warnings[-1].getMessage()


def test_capped_job_is_never_claimed_again(db_session, monkeypatch) -> None:
    """回归：无限「认领 → 超时 → 再认领」循环必须被 attempt 上限截断。"""
    monkeypatch.setattr(config.settings, "ai_job_max_attempts", 3)
    ai_agent_service.register_agent(db_session, "agent-a", 7, ["extract"], issue_token=False)
    created = ai_agent_service.create_job(db_session, project_id=7, job_type="extract", payload={})

    claimed_ids: list[int] = []
    for _ in range(3):
        claimed = _claim(db_session)
        assert claimed is not None, "上限内仍应可以认领"
        claimed_ids.append(claimed.id)
        _make_stale(db_session, claimed)

    # 第 4 次认领：回收时发现已到上限 → 终态 failed，不再返回任务
    assert _claim(db_session) is None
    assert _claim(db_session) is None

    job = db_session.get(AiJob, created.id)
    assert job is not None
    assert job.status == "failed"
    assert job.attempt_count == 3
    assert set(claimed_ids) == {created.id}
