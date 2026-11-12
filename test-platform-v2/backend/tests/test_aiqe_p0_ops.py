"""P0：Dispatch + Artifact GC 单测。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services.artifact_gc import purge_expired_artifacts
from app.aiqe.services.artifact_storage import LocalArtifactStorage
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.models.execution_job import ExecutionJob


def make_run_node(db):
    run = TestRun(project_id=1, run_key=f"run-{uuid.uuid4()}", status="RUNNING")
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="api-check", status="READY")
    db.add(node)
    db.flush()
    return run, node


def test_dispatch_creates_linked_job(db_session):
    _run, node = make_run_node(db_session)
    job = enqueue_node_run(db_session, node)
    assert job.status == "pending"
    assert job.project_id == 1
    assert f'"node_key": "api-check"' in job.payload_json
    assert node.execution_job_id == job.id


def test_dispatch_is_idempotent(db_session):
    _run, node = make_run_node(db_session)
    first = enqueue_node_run(db_session, node)
    second = enqueue_node_run(db_session, node)
    assert first.id == second.id
    assert db_session.query(ExecutionJob).count() == 1


def test_gc_removes_expired_artifact(db_session, tmp_path):
    run, _node = make_run_node(db_session)
    storage = LocalArtifactStorage(tmp_path)
    uri = storage.put(b"old", "a" * 64)
    row = RunArtifact(
        run_id=run.id,
        artifact_type="log",
        storage_uri=uri,
        sha256="a" * 64,
        size_bytes=3,
        created_at=datetime.now(UTC) - timedelta(days=40),
    )
    db_session.add(row)
    db_session.flush()

    result = purge_expired_artifacts(db_session, retention_days=30, storage=storage)
    assert result["deleted"] == 1
    assert result["failed"] == 0
    assert db_session.get(RunArtifact, row.id) is None
    assert not storage._path_for("a" * 64).exists()


def test_gc_keeps_recent_artifact(db_session, tmp_path):
    run, _node = make_run_node(db_session)
    storage = LocalArtifactStorage(tmp_path)
    uri = storage.put(b"new", "b" * 64)
    row = RunArtifact(
        run_id=run.id,
        artifact_type="log",
        storage_uri=uri,
        sha256="b" * 64,
        size_bytes=3,
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(row)
    db_session.flush()
    result = purge_expired_artifacts(db_session, retention_days=30, storage=storage)
    assert result["deleted"] == 0
    assert db_session.get(RunArtifact, row.id) is not None


def test_gc_storage_failure_keeps_row(db_session):
    run, _node = make_run_node(db_session)
    row = RunArtifact(
        run_id=run.id,
        artifact_type="log",
        storage_uri="s3://bucket/missing",
        sha256="c" * 64,
        created_at=datetime.now(UTC) - timedelta(days=40),
    )
    db_session.add(row)
    db_session.flush()

    class BrokenStorage:
        def delete(self, uri):
            raise RuntimeError("storage down")

    result = purge_expired_artifacts(db_session, retention_days=30, storage=BrokenStorage())
    assert result["failed"] == 1
    assert db_session.get(RunArtifact, row.id) is not None
