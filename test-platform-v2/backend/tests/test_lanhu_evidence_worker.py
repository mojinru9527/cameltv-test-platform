"""Persistent Lanhu evidence worker and immutable retry tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path


def test_claim_next_job_marks_only_one_pending_job_running(db_session):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.worker import claim_next_job

    first = LanhuEvidenceJob(project_id=1, source_url="first", status="pending")
    second = LanhuEvidenceJob(project_id=1, source_url="second", status="pending")
    db_session.add_all([first, second])
    db_session.commit()

    claimed = claim_next_job(db_session)

    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status == "running"
    assert claimed.stage == "discovering"
    assert claimed.heartbeat_at is not None
    db_session.refresh(second)
    assert second.status == "pending"


def test_recover_stale_job_marks_failed_with_worker_lost(db_session):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.worker import recover_stale_jobs

    stale = LanhuEvidenceJob(
        project_id=1,
        status="running",
        heartbeat_at=datetime.now() - timedelta(minutes=11),
    )
    healthy = LanhuEvidenceJob(
        project_id=1,
        status="running",
        heartbeat_at=datetime.now(),
    )
    db_session.add_all([stale, healthy])
    db_session.commit()

    assert recover_stale_jobs(db_session, stale_after_seconds=600) == 1
    db_session.refresh(stale)
    db_session.refresh(healthy)
    assert stale.status == "failed"
    assert stale.stage == "done"
    assert stale.error_message == "worker_lost"
    assert stale.finished_at is not None
    assert healthy.status == "running"


def test_task_worker_polls_evidence_worker_once(monkeypatch):
    from app.services import task_worker
    from app.services.lanhu_evidence import worker

    calls = []
    monkeypatch.setattr(task_worker, "_process_api_tasks", lambda: calls.append("api"))
    monkeypatch.setattr(task_worker, "_process_ui_runs", lambda: calls.append("ui"))
    monkeypatch.setattr(worker, "poll_and_execute_evidence_jobs", lambda: calls.append("lanhu"))

    task_worker.poll_and_execute()

    assert calls == ["api", "ui", "lanhu"]


def test_create_job_does_not_execute_in_request_background(
    client, auth_headers, monkeypatch,
):
    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)

    def _must_not_run(*_args, **_kwargs):
        raise AssertionError("request handler must only persist a pending job")

    monkeypatch.setattr(
        "app.services.lanhu_evidence.job_runner.run_job_in_new_session", _must_not_run,
    )

    response = client.post(
        "/api/v1/lanhu-evidence/jobs",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=d"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "pending"


def test_retry_creates_immutable_attempt_and_preserves_original(
    client, auth_headers, db_session, monkeypatch, tmp_path,
):
    from app.models.lanhu_evidence import (
        LanhuEvidenceAsset,
        LanhuEvidenceJob,
        LanhuEvidencePage,
    )

    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    original_dir = tmp_path / "original" / "attempt-1"
    original = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        status="failed",
        stage="done",
        storage_dir=str(original_dir),
        requested_options_json=json.dumps({
            "capture_all_pages": False,
            "include_word": False,
            "include_json": True,
            "import_to_requirement": False,
            "import_to_knowledge": True,
            "import_to_wiki": False,
        }),
        attempt_no=1,
        error_message="worker_lost",
    )
    db_session.add(original)
    db_session.flush()
    page = LanhuEvidencePage(
        job_id=original.id,
        project_id=1,
        page_id="p1",
        capture_status="success",
    )
    db_session.add(page)
    db_session.flush()
    asset = LanhuEvidenceAsset(
        job_id=original.id,
        page_id=page.id,
        project_id=1,
        asset_type="screenshot",
        file_path=str(original_dir / "p1.png"),
    )
    db_session.add(asset)
    db_session.commit()

    response = client.post(
        f"/api/v1/lanhu-evidence/jobs/{original.id}/retry", headers=auth_headers,
    )

    assert response.status_code == 200
    new_id = response.json()["data"]["id"]
    assert new_id != original.id
    db_session.expire_all()
    old = db_session.get(LanhuEvidenceJob, original.id)
    retried = db_session.get(LanhuEvidenceJob, new_id)
    assert old.status == "failed"
    assert old.error_message == "worker_lost"
    assert db_session.query(LanhuEvidencePage).filter_by(job_id=old.id).count() == 1
    assert db_session.query(LanhuEvidenceAsset).filter_by(job_id=old.id).count() == 1
    assert retried.status == "pending"
    assert retried.parent_job_id == old.id
    assert retried.attempt_no == 2
    assert retried.requested_options_json == old.requested_options_json
    assert Path(retried.storage_dir).parts[-2:] == (str(retried.id), "attempt-2")
    assert retried.storage_dir != old.storage_dir


def test_heartbeat_interval_stays_inside_stale_window():
    from app.services.lanhu_evidence.job_runner import heartbeat_interval

    assert heartbeat_interval(600) == 30.0
    assert heartbeat_interval(8) < 8 / 2


def test_dom_text_for_skips_image_files(tmp_path):
    """设计图板原图（PNG）不应进入 DOM 文本，避免二进制混入 merged_text。"""
    from app.services.lanhu_evidence.job_runner import _dom_text_for

    png = tmp_path / "design.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    html = tmp_path / "card.html"
    html.write_text("<html><body>批注：金额高度 64px 改 68px</body></html>", encoding="utf-8")

    assert _dom_text_for(png.as_uri()) == ""
    assert "金额高度" in _dom_text_for(html.as_uri())


def test_resume_failed_job_reuses_captured_pages(tmp_path):
    """断点续跑：failed 任务从已持久化页面恢复导出/终态，不重跑截图/OCR。"""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401 — 注册全部模型
    from app.core.db import Base
    from app.models.lanhu_evidence import (
        LanhuEvidenceAsset,
        LanhuEvidenceJob,
        LanhuEvidencePage,
    )
    from app.services.lanhu_evidence.job_runner import resume_failed_job_in_new_session

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.add(LanhuEvidenceJob(
            id=1,
            project_id=1,
            source_url="https://lanhuapp.com/web/#/item/project/stage?tid=t&pid=p",
            status="failed",
            stage="done",
            captured_pages=1,
            creator_id=1,
            storage_dir=str(tmp_path),
            requested_options_json='{"include_word": true, "include_json": true}',
        ))
        s.add(LanhuEvidencePage(
            job_id=1,
            project_id=1,
            page_id="p1",
            page_name="赛事回放",
            page_path="设计图板/赛事回放",
            folder="设计图板",
            order_index=0,
            capture_status="success",
            ocr_status="success",
            segment_count=1,
            merged_text="# 赛事回放\n## OCR识别文本\n9:41 赛事\x00回放",
            quality_json='{"status":"success"}',
        ))
        s.commit()

    resume_failed_job_in_new_session(1, 1, session_factory=Session)

    with Session() as s:
        job = s.get(LanhuEvidenceJob, 1)
        assert job.status == "success"
        assert job.stage == "done"
        assert job.quality_json
        assert "import_ready" in job.quality_json
        assets = s.execute(
            select(LanhuEvidenceAsset).where(LanhuEvidenceAsset.job_id == 1)
        ).scalars().all()
        assert {a.asset_type for a in assets} == {"word", "json"}
    assert (tmp_path / "lanhu.docx").exists()
    assert (tmp_path / "lanhu.json").exists()
