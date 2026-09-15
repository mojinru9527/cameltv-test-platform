from __future__ import annotations

from app.models.ai_job import AiJob
from app.services import ai_agent_service


def test_ai_agent_claim_heartbeat_report(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-local", 1, ["extract"])
    job = AiJob(project_id=1, job_type="extract", status="pending", capability="extract")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    claimed = ai_agent_service.claim_job(db_session, "agent-local", ["extract"])
    assert claimed is not None and claimed.id == job.id
    assert ai_agent_service.heartbeat_job(db_session, job.id, "agent-local") is True
    reported = ai_agent_service.report_job(
        db_session, job.id, "agent-local", "completed", "ok", {"items": [1]}, [], "qwen-local", ""
    )
    assert reported is not None and reported.status == "completed"


def test_ai_agent_cannot_claim_without_capability(db_session) -> None:
    ai_agent_service.register_agent(db_session, "agent-local", 1, ["extract"])
    db_session.add(AiJob(project_id=1, job_type="generate", status="pending", capability="generate"))
    db_session.commit()
    assert ai_agent_service.claim_job(db_session, "agent-local", ["extract"]) is None
