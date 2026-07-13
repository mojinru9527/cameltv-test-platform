"""证据包任务编排与导入测试。"""
from __future__ import annotations


def test_job_runner_marks_job_failed_when_discovery_fails(db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.job_runner import run_job_in_new_session

    job = LanhuEvidenceJob(project_id=1, source_url="bad", status="pending", storage_dir="x")
    db_session.add(job)
    db_session.commit()

    def _boom(*args, **kwargs):
        raise ValueError("invalid url")

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages", _boom
    )

    run_job_in_new_session(job.id, project_id=1, session_factory=lambda: db_session)

    refreshed = db_session.get(LanhuEvidenceJob, job.id)
    assert refreshed.status == "failed"
    assert "invalid url" in refreshed.error_message


def test_job_runner_marks_cancelled_when_cancel_requested(db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.job_runner import run_job_in_new_session
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1, source_url="https://lanhuapp.com/x?docId=d",
        status="pending", storage_dir="x", cancel_requested=True,
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [DiscoveredLanhuPage("p1", "页", "页", "", 0)],
    )

    run_job_in_new_session(job.id, project_id=1, session_factory=lambda: db_session)

    refreshed = db_session.get(LanhuEvidenceJob, job.id)
    assert refreshed.status == "cancelled"
