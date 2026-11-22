"""V16-018 验收：Artifact 安全、完整性与 Evidence Lifecycle。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.aiqe.models.event import RunEvent
from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services.artifact_service import (
    ArtifactAccessDenied,
    InvalidArtifact,
    complete_upload,
    create_pending_artifact,
    evidence_ref_metadata,
    fail_stale_pending_uploads,
    incompleteness_reasons,
    open_download,
    put_artifact,
)
from app.aiqe.services.artifact_storage import ArtifactStorageError, LocalArtifactStorage
from app.models.project import Project


@pytest.fixture()
def storage(tmp_path):
    return LocalArtifactStorage(tmp_path / "artifacts")


def _run(db, *, key: str = "RUN-ART-1", project_id: int = 1) -> TestRun:
    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()
    run = TestRun(project_id=project_id, run_key=key, status="RUNNING")
    db.add(run)
    db.flush()
    return run


def _pending(db, run, **kwargs):
    row, target = create_pending_artifact(
        db,
        project_id=int(run.project_id),
        run_id=run.id,
        artifact_type=kwargs.pop("artifact_type", "SCREENSHOT"),
        **kwargs,
    )
    return row, target


def test_upload_session_expiry_rejects_finalize(db_session, storage):
    t0 = datetime.now(UTC) - timedelta(hours=2)
    run = _run(db_session, key="RUN-ART-EXP")
    row, _target = _pending(db_session, run, content_type="image/png", now=t0)
    with pytest.raises(InvalidArtifact):
        complete_upload(
            db_session,
            artifact_id=row.id,
            project_id=1,
            content=b"png-bytes",
            storage=storage,
        )
    db_session.refresh(row)
    assert row.upload_status == "FAILED"
    assert (row.metadata_json or {}).get("upload_error") == "UPLOAD_SESSION_EXPIRED"
    with pytest.raises(InvalidArtifact):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)


def test_content_type_mismatch_rejected(db_session, storage):
    run = _run(db_session, key="RUN-ART-MIME")
    row, _ = _pending(db_session, run, content_type="application/json")
    with pytest.raises(InvalidArtifact):
        complete_upload(
            db_session, artifact_id=row.id, project_id=1, content=b"{}", storage=storage
        )
    # 默认 octet-stream（未声明）允许
    ok_row, _ = _pending(db_session, run, content_type="application/octet-stream")
    complete_upload(
        db_session, artifact_id=ok_row.id, project_id=1, content=b"png", storage=storage
    )
    assert ok_row.upload_status == "AVAILABLE"


def test_expected_size_mismatch_rejected(db_session, storage):
    run = _run(db_session, key="RUN-ART-SIZE")
    row, _ = _pending(db_session, run, content_type="image/png", expected_size_bytes=10)
    with pytest.raises(InvalidArtifact):
        complete_upload(
            db_session, artifact_id=row.id, project_id=1, content=b"123", storage=storage
        )
    db_session.refresh(row)
    assert row.upload_status == "FAILED"


def test_step_attempt_from_other_run_rejected(db_session):
    run = _run(db_session, key="RUN-ART-A")
    other = _run(db_session, key="RUN-ART-B")
    node = NodeRun(run_id=other.id, node_key="n", driver_key="http", status="RUNNING")
    db_session.add(node)
    db_session.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="n", attempt_no=1, status="RUNNING")
    db_session.add(attempt)
    db_session.flush()
    with pytest.raises(InvalidArtifact):
        create_pending_artifact(
            db_session,
            project_id=1,
            run_id=run.id,
            artifact_type="SCREENSHOT",
            step_attempt_id=attempt.id,
        )


def test_cross_project_download_denied(db_session, storage):
    run = _run(db_session, key="RUN-ART-X")
    row, _ = _pending(db_session, run, content_type="image/png")
    complete_upload(
        db_session, artifact_id=row.id, project_id=1, content=b"png", storage=storage
    )
    with pytest.raises((ArtifactAccessDenied, InvalidArtifact)):
        open_download(db_session, artifact_id=row.id, project_id=2, storage=storage)


def test_tombstoned_evidence_ref_is_explicitly_unavailable(db_session, storage):
    run = _run(db_session, key="RUN-ART-TOMB")
    row, _ = _pending(db_session, run, content_type="image/png")
    complete_upload(
        db_session, artifact_id=row.id, project_id=1, content=b"png", storage=storage
    )
    row.upload_status = "PURGED"
    db_session.flush()
    meta = evidence_ref_metadata(db_session, row.id, 1)
    assert meta["available"] is False
    assert meta["reason"] == "EVIDENCE_TOMBSTONED"
    with pytest.raises(InvalidArtifact):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)


def test_download_records_access_event(db_session, storage):
    run = _run(db_session, key="RUN-ART-AUDIT")
    row, _ = _pending(db_session, run, content_type="image/png")
    complete_upload(
        db_session, artifact_id=row.id, project_id=1, content=b"png", storage=storage
    )
    db_session.commit()
    _row, content = open_download(
        db_session, artifact_id=row.id, project_id=1, storage=storage
    )
    assert content == b"png"
    db_session.commit()
    events = list(
        db_session.scalars(
            select(RunEvent).where(
                RunEvent.run_id == run.id, RunEvent.event_type == "artifact.accessed"
            )
        )
    )
    assert events and events[-1].payload_json["artifact_id"] == row.id


def test_stale_pending_upload_marked_failed_and_blocks_evidence(db_session, storage):
    run = _run(db_session, key="RUN-ART-STALE")
    row, _ = _pending(db_session, run, content_type="image/png")
    row.created_at = datetime.now(UTC) - timedelta(hours=3)
    db_session.flush()
    assert fail_stale_pending_uploads(db_session, stale_after_minutes=60) == 1
    db_session.refresh(row)
    assert row.upload_status == "FAILED"
    assert incompleteness_reasons(db_session, run.id)


def test_forged_storage_uri_rejected(db_session, storage, tmp_path):
    run = _run(db_session, key="RUN-ART-FORGE")
    row = put_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        content=b"data",
        artifact_type="CONSOLE_LOG",
        mime_type="text/plain",
        storage=storage,
    )
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    row.storage_uri = f"file://{outside}"
    db_session.flush()
    with pytest.raises(ArtifactStorageError):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)
