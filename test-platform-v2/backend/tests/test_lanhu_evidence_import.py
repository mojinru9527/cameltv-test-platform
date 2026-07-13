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


# ── API ──

def test_create_job_returns_503_when_disabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", False)
    resp = client.post(
        "/api/v1/lanhu-evidence/jobs",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=d"},
    )
    assert resp.status_code == 503


def test_create_and_get_job_when_enabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    # 阻断后台真实采集
    monkeypatch.setattr(
        "app.services.lanhu_evidence.job_runner.run_job_in_new_session",
        lambda *a, **k: None,
    )
    resp = client.post(
        "/api/v1/lanhu-evidence/jobs",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=d"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    job_id = data["id"]

    got = client.get(f"/api/v1/lanhu-evidence/jobs/{job_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == job_id


def test_get_job_isolated_by_project(client, auth_headers, db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    # 属于项目 999 的任务，当前请求头项目为 1 → 404
    other = LanhuEvidenceJob(project_id=999, source_url="x", status="success", storage_dir="x")
    db_session.add(other)
    db_session.commit()

    resp = client.get(f"/api/v1/lanhu-evidence/jobs/{other.id}", headers=auth_headers)
    assert resp.status_code == 404

