"""M1 / TA-007：Artifact Manager 单测（13 号 §4.12）。"""
from __future__ import annotations

import hashlib

import pytest

from app.aiqe.models.run import TestRun
from app.aiqe.services.artifact_service import (
    ArtifactAccessDenied,
    InvalidArtifact,
    get_artifact,
    list_artifacts,
    mark_redaction,
    put_artifact,
    read_artifact,
)
from app.aiqe.services.artifact_storage import ArtifactStorageError, LocalArtifactStorage


def _run(db, project_id=1, key="RUN-20261110-00001") -> TestRun:
    run = TestRun(project_id=project_id, run_key=key, source_type="manual", status="RUNNING")
    db.add(run)
    db.flush()
    return run


def test_put_and_read_roundtrip(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    content = b"hello-artifact"
    digest = hashlib.sha256(content).hexdigest()

    row = put_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        content=content,
        artifact_type="log",
        mime_type="text/plain",
        metadata={"source": "unit"},
        storage=storage,
    )
    db_session.commit()

    assert row.sha256 == digest
    assert row.size_bytes == len(content)
    assert row.storage_uri == f"file://{tmp_path / digest[:2] / digest[2:4] / digest}"
    assert row.redaction_status == "pending"
    assert read_artifact(db_session, row.id, 1, storage=storage) == content


def test_same_content_dedupes_file(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    content = b"same-bytes"
    a = put_artifact(
        db_session, project_id=1, run_id=run.id, content=content, artifact_type="trace", storage=storage
    )
    b = put_artifact(
        db_session, project_id=1, run_id=run.id, content=content, artifact_type="trace", storage=storage
    )
    db_session.commit()
    assert a.id != b.id
    assert a.storage_uri == b.storage_uri
    assert len(list(tmp_path.rglob("*"))) == 3  # 2 dirs + 1 file


def test_cross_project_access_denied(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    row = put_artifact(
        db_session, project_id=1, run_id=run.id, content=b"x", artifact_type="log", storage=storage
    )
    db_session.commit()
    with pytest.raises(ArtifactAccessDenied):
        get_artifact(db_session, row.id, 2)
    with pytest.raises(ArtifactAccessDenied):
        read_artifact(db_session, row.id, 2, storage=storage)
    with pytest.raises(ArtifactAccessDenied):
        list_artifacts(db_session, run.id, 2)
    with pytest.raises(ArtifactAccessDenied):
        mark_redaction(db_session, row.id, 2, "sanitized")


def test_invalid_inputs(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    with pytest.raises(InvalidArtifact):
        put_artifact(
            db_session, project_id=1, run_id=run.id, content=b"x", artifact_type="exe", storage=storage
        )
    with pytest.raises(InvalidArtifact):
        put_artifact(
            db_session,
            project_id=1,
            run_id=run.id,
            content=b"x",
            artifact_type="log",
            linked_evidence_type="lanhu_evidence",
            storage=storage,
        )
    with pytest.raises(InvalidArtifact):
        put_artifact(
            db_session, project_id=1, run_id="missing", content=b"x", artifact_type="log", storage=storage
        )


def test_redaction_transitions(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    row = put_artifact(
        db_session, project_id=1, run_id=run.id, content=b"pii", artifact_type="screenshot", storage=storage
    )
    db_session.commit()
    assert mark_redaction(db_session, row.id, 1, "sanitized").redaction_status == "sanitized"
    with pytest.raises(InvalidArtifact):
        mark_redaction(db_session, row.id, 1, "rejected")

    other = put_artifact(
        db_session, project_id=1, run_id=run.id, content=b"pii2", artifact_type="screenshot", storage=storage
    )
    db_session.commit()
    assert mark_redaction(db_session, other.id, 1, "rejected").redaction_status == "rejected"


def test_read_rejects_path_escape(db_session, tmp_path):
    run = _run(db_session)
    storage = LocalArtifactStorage(tmp_path)
    row = put_artifact(
        db_session, project_id=1, run_id=run.id, content=b"x", artifact_type="log", storage=storage
    )
    db_session.commit()
    row.storage_uri = "file:///etc/passwd"
    with pytest.raises(ArtifactStorageError):
        read_artifact(db_session, row.id, 1, storage=storage)
