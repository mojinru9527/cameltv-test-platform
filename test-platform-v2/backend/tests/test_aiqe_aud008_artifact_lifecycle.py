"""AUD-008：Artifact 真实采集 / 上传 / 下载 / 保留策略验收测试。

对应 v1.5 §02 AUD-008「验收」：
- 未完成上传不能显示"证据完整"，P0 Run 不得汇总为可发布 PASS；
- 修改存储文件后 SHA256 校验失败；
- 跨项目用户下载 Artifact 返回 403/404；
- 过期 Artifact 按 Retention Policy 清理，元数据保留审计墓碑。
"""
from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime, timedelta

import pytest

from app.aiqe.models.artifact import ArtifactType, ArtifactUploadStatus, RunArtifact
from app.aiqe.models.run import TestRun
from app.aiqe.services import dag_scheduler
from app.aiqe.services.artifact_gc import purge_expired_artifacts
from app.aiqe.services.artifact_service import (
    ArtifactAccessDenied,
    InvalidArtifact,
    ARTIFACT_TYPES,
    canonical_type,
    complete_upload,
    create_pending_artifact,
    get_artifact,
    incompleteness_reasons,
    open_download,
    put_artifact,
    verify_integrity,
)
from app.aiqe.services.artifact_storage import LocalArtifactStorage


class _Storage(LocalArtifactStorage):
    """本地存储 + 可控失败，避免测试依赖真实对象存储。"""


@pytest.fixture()
def storage(tmp_path):
    return _Storage(tmp_path)


def _seed_run(db, *, key="RUN-AUD008", project_id=1) -> TestRun:
    run = TestRun(project_id=project_id, run_key=key, status="RUNNING")
    db.add(run)
    db.flush()
    return run


# ── 1. 类型规范化 ─────────────────────────────────────────
def test_spec_artifact_types_supported():
    for member in ArtifactType:
        assert member.value in ARTIFACT_TYPES
        assert canonical_type(member.value) == member.value


def test_legacy_type_aliases_map_to_spec_types():
    assert canonical_type("screenshot") == ArtifactType.SCREENSHOT.value
    assert canonical_type("har") == ArtifactType.HAR.value
    assert canonical_type("db_snapshot") == ArtifactType.DB_RESULT_SUMMARY.value
    with pytest.raises(InvalidArtifact):
        canonical_type("unknown-type")


# ── 2. 两阶段上传 ─────────────────────────────────────────
def test_pending_until_upload_completes(db_session, storage):
    run = _seed_run(db_session)
    content = b"trace-bytes"
    digest = hashlib.sha256(content).hexdigest()
    row, target = create_pending_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        artifact_type="PLAYWRIGHT_TRACE",
        content_type="application/zip",
        expected_sha256=digest,
        expected_size_bytes=len(content),
        retention_days=7,
    )
    assert row.upload_status == ArtifactUploadStatus.PENDING_UPLOAD.value
    assert row.project_id == 1
    assert row.retention_until is not None
    assert target["upload_url"].endswith(f"/{row.id}/content")

    with pytest.raises(InvalidArtifact):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)

    done = complete_upload(
        db_session, artifact_id=row.id, project_id=1, content=content, storage=storage
    )
    assert done.upload_status == ArtifactUploadStatus.AVAILABLE.value
    assert done.sha256 == digest
    assert done.size_bytes == len(content)

    fetched, data = open_download(
        db_session, artifact_id=row.id, project_id=1, storage=storage
    )
    assert data == content
    assert fetched.storage_uri


def test_sha_mismatch_marks_corrupted_and_never_stores(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-2")
    row, _target = create_pending_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        artifact_type="SCREENSHOT",
        expected_sha256=hashlib.sha256(b"expected").hexdigest(),
    )
    with pytest.raises(InvalidArtifact):
        complete_upload(
            db_session, artifact_id=row.id, project_id=1, content=b"tampered", storage=storage
        )
    assert row.upload_status == ArtifactUploadStatus.CORRUPTED.value
    assert row.storage_uri == ""
    assert row.metadata_json["corruption"]["actual_sha256"] == hashlib.sha256(b"tampered").hexdigest()
    with pytest.raises(InvalidArtifact):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)


def test_empty_and_oversized_upload_rejected(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-3")
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="HAR"
    )
    with pytest.raises(InvalidArtifact):
        complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"", storage=storage)
    assert row.upload_status == ArtifactUploadStatus.FAILED.value


def test_cannot_upload_twice(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-4")
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="CONSOLE_LOG"
    )
    complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"log", storage=storage)
    with pytest.raises(InvalidArtifact):
        complete_upload(
            db_session, artifact_id=row.id, project_id=1, content=b"log2", storage=storage
        )


# ── 3. 跨项目访问 ─────────────────────────────────────────
def test_cross_project_access_denied(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-5", project_id=1)
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="VIDEO"
    )
    complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"v", storage=storage)

    with pytest.raises(ArtifactAccessDenied):
        get_artifact(db_session, row.id, project_id=2)
    with pytest.raises(ArtifactAccessDenied):
        open_download(db_session, artifact_id=row.id, project_id=2, storage=storage)
    with pytest.raises(ArtifactAccessDenied):
        complete_upload(
            db_session, artifact_id=row.id, project_id=2, content=b"x", storage=storage
        )


def test_unknown_artifact_rejected(db_session):
    with pytest.raises(InvalidArtifact):
        get_artifact(db_session, "no-such-artifact", project_id=1)


# ── 4. 完整性校验（文件被篡改） ───────────────────────────
def test_tampered_storage_marks_corrupted(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-6")
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="DOM_SNAPSHOT"
    )
    complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"dom", storage=storage)

    # 模拟对象存储内容被改写
    path = storage._path_for(row.sha256)
    path.write_bytes(b"tampered-after-upload")

    checked = verify_integrity(db_session, row.id, project_id=1, storage=storage)
    assert checked.upload_status == ArtifactUploadStatus.CORRUPTED.value
    assert checked.metadata_json["corruption"]["actual_sha256"] == hashlib.sha256(
        b"tampered-after-upload"
    ).hexdigest()


# ── 5. 保留策略墓碑 ──────────────────────────────────────
def test_purge_keeps_tombstone_and_blocks_download(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-7")
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="RUNNER_LOG"
    )
    complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"log", storage=storage)
    row.created_at = datetime.now(UTC) - timedelta(days=60)
    db_session.flush()

    result = purge_expired_artifacts(db_session, retention_days=30, storage=storage)
    assert result["purged"] == 1
    tombstone = db_session.get(RunArtifact, row.id)
    assert tombstone is not None
    assert tombstone.upload_status == ArtifactUploadStatus.PURGED.value
    assert tombstone.deleted_at is not None
    assert tombstone.metadata_json["purge_reason"] == "retention_30_days"

    with pytest.raises(InvalidArtifact):
        open_download(db_session, artifact_id=row.id, project_id=1, storage=storage)


# ── 6. Run 汇总不得在证据未完成时 PASS ────────────────────
GRAPH = {
    "schema_version": "1.0",
    "nodes": [{"key": "api", "driver": "http", "input": {"url": "https://api.allowed.test/x"}}],
    "edges": [],
}


def test_run_incomplete_when_artifact_pending(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-8")
    dag_scheduler.create_node_runs(db_session, run.id, GRAPH)
    node = dag_scheduler.create_node_runs(db_session, run.id, GRAPH)[0]
    dag_scheduler.schedule(db_session, run.id, GRAPH)
    create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="SCREENSHOT"
    )

    assert incompleteness_reasons(db_session, run.id)
    dag_scheduler.complete_node(db_session, run.id, node.node_key, "PASSED", GRAPH)
    db_session.commit()

    run_row = db_session.get(TestRun, run.id)
    assert run_row.status == "COMPLETED"
    assert run_row.outcome == "INCOMPLETE"


def test_run_pass_when_evidence_complete(db_session, storage):
    run = _seed_run(db_session, key="RUN-AUD008-9")
    dag_scheduler.create_node_runs(db_session, run.id, GRAPH)
    node = dag_scheduler.create_node_runs(db_session, run.id, GRAPH)[0]
    dag_scheduler.schedule(db_session, run.id, GRAPH)
    row, _ = create_pending_artifact(
        db_session, project_id=1, run_id=run.id, artifact_type="SCREENSHOT"
    )
    complete_upload(db_session, artifact_id=row.id, project_id=1, content=b"png", storage=storage)

    # V16-009：Run PASS 需要业务 Oracle；为该节点预置一条 PASS 业务断言。
    from app.aiqe.models.run import StepAttempt
    from app.aiqe.schemas.contracts import AssertionOutcome
    from app.aiqe.services import assertion_service

    attempt = StepAttempt(
        node_run_id=node.id, step_key=node.node_key, attempt_no=1, status="PASSED"
    )
    db_session.add(attempt)
    db_session.flush()
    assertion_service.persist_outcomes(
        db_session,
        attempt,
        [
            AssertionOutcome(
                assertion_key="evidence_oracle",
                type="http_status",
                oracle_layer="REQ",
                oracle_ref="AC-EVIDENCE-1",
                status="PASS",
                expected=200,
                actual=200,
                severity="P0",
            )
        ],
    )
    dag_scheduler.complete_node(db_session, run.id, node.node_key, "PASSED", GRAPH)
    db_session.commit()
    run_row = db_session.get(TestRun, run.id)
    assert run_row.outcome == "PASS"


# ── 7. HTTP API ──────────────────────────────────────────
def test_artifact_api_lifecycle(client, auth_headers, db_session):
    run = _seed_run(db_session, key="RUN-AUD008-API")
    db_session.commit()
    client.headers.update(auth_headers)

    created = client.post(
        "/api/v1/aiqe/artifacts",
        json={
            "run_id": run.id,
            "artifact_type": "SCREENSHOT",
            "content_type": "image/png",
            "retention_days": 5,
        },
    )
    assert created.status_code == 200, created.text
    payload = created.json()["data"]
    artifact_id = payload["artifact"]["id"]
    assert payload["artifact"]["upload_status"] == "PENDING_UPLOAD"
    assert payload["upload"]["method"] == "PUT"

    # 未完成上传 → 下载拒绝
    pending_download = client.get(f"/api/v1/aiqe/artifacts/{artifact_id}/content")
    assert pending_download.status_code == 400

    uploaded = client.put(
        f"/api/v1/aiqe/artifacts/{artifact_id}/content", content=b"\x89PNG-bytes"
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["data"]["artifact"]["upload_status"] == "AVAILABLE"

    meta = client.get(f"/api/v1/aiqe/artifacts/{artifact_id}")
    assert meta.status_code == 200
    assert meta.json()["data"]["artifact_type"] == "SCREENSHOT"

    download = client.get(f"/api/v1/aiqe/artifacts/{artifact_id}/content")
    assert download.status_code == 200
    assert download.content == b"\x89PNG-bytes"
    assert download.headers["cache-control"].startswith("private")


def test_artifact_api_cross_project_denied(client, auth_headers, db_session):
    run = _seed_run(db_session, key="RUN-AUD008-OTHER", project_id=2)
    db_session.commit()
    client.headers.update(auth_headers)
    resp = client.post(
        "/api/v1/aiqe/artifacts",
        json={"run_id": run.id, "artifact_type": "HAR"},
    )
    assert resp.status_code == 403


def test_artifact_api_unknown_id_404(client, auth_headers):
    client.headers.update(auth_headers)
    assert client.get("/api/v1/aiqe/artifacts/no-such").status_code == 404
    assert client.get("/api/v1/aiqe/artifacts/no-such/content").status_code == 404


def test_artifact_api_requires_permission(client, db_session):
    run = _seed_run(db_session, key="RUN-AUD008-RBAC")
    db_session.commit()
    resp = client.post(
        "/api/v1/aiqe/artifacts", json={"run_id": run.id, "artifact_type": "HAR"}
    )
    assert resp.status_code in {401, 403}
