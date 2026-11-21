"""V16-015 验收：Capability 真实性（VERIFIED 只来自真实验收 Run）/ Preflight 策略。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.aiqe.models.artifact import ArtifactType, ArtifactUploadStatus, RunArtifact
from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.run import TestRun
from app.aiqe.services import capability_registry
from app.aiqe.services.preflight import preflight_graph
from app.models.project import Project


def _project(db, project_id: int = 1) -> None:
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


def _manifest(db, node_id: str = "node-http") -> NodeCapabilityManifest:
    _project(db)
    return capability_registry.register_manifest(
        db,
        node_id=node_id,
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://initial",
        runner_version="1.0.0",
    )


def _run(db, *, key: str, status: str = "COMPLETED", outcome: str | None = "PASS") -> TestRun:
    _project(db)
    run = TestRun(project_id=1, run_key=key, status=status, outcome=outcome)
    db.add(run)
    db.flush()
    return run


def _artifact(db, run: TestRun, *, status: str = "AVAILABLE", run_id: str | None = None) -> RunArtifact:
    row = RunArtifact(
        project_id=int(run.project_id),
        run_id=run_id or run.id,
        artifact_type=ArtifactType.SCREENSHOT,
        storage_uri="artifact://x",
        sha256="a" * 64,
        upload_status=status,
        size_bytes=1,
    )
    db.add(row)
    db.flush()
    return row


GRAPH = {
    "schema_version": "1.0",
    "nodes": [{"key": "api", "driver": "http", "input": {"url": "https://api.test/x"}}],
    "edges": [],
}


def test_verify_from_run_writes_evidence_and_verified(db_session):
    _manifest(db_session)
    run = _run(db_session, key="CAP-OK")
    artifact = _artifact(db_session, run)
    row = capability_registry.verify_from_run(
        db_session,
        "node-http",
        project_id=1,
        verification_run_id=run.id,
        artifact_ids=[artifact.id],
        platforms=["linux", "chromium"],
        runner_image_digest="sha256:" + "b" * 64,
        os_version="ubuntu-24.04",
        browser_version="149.0.7827.55",
        supported_actions=["navigate", "click", "screenshot"],
        limitations=["no-video"],
    )
    assert row.capability_status == "VERIFIED"
    assert row.verification_run_id == run.id
    assert row.verification_artifact_refs_json == [f"artifact:{artifact.id}@sha256:{artifact.sha256}"]
    assert row.verified_platforms_json == ["chromium", "linux"]
    assert row.browser_version == "149.0.7827.55"
    assert row.runner_image_digest.endswith("b" * 64)
    assert row.verified_at is not None


def test_verify_requires_completed_pass_run(db_session):
    _manifest(db_session)
    artifact = _artifact(db_session, _run(db_session, key="CAP-A"))
    for status, outcome in (("RUNNING", None), ("COMPLETED", "FAIL"), ("COMPLETED", "INCOMPLETE")):
        run = _run(db_session, key=f"CAP-{status}-{outcome}", status=status, outcome=outcome)
        art = _artifact(db_session, run)
        with pytest.raises(capability_registry.CapabilityError):
            capability_registry.verify_from_run(
                db_session,
                "node-http",
                project_id=1,
                verification_run_id=run.id,
                artifact_ids=[art.id],
                platforms=["linux"],
            )
    assert artifact.run_id


def test_verify_requires_same_run_available_artifacts(db_session):
    _manifest(db_session)
    run = _run(db_session, key="CAP-OK2")
    other = _run(db_session, key="CAP-OTHER")
    other_artifact = _artifact(db_session, other)
    pending = _artifact(db_session, run, status="PENDING_UPLOAD")
    for args in ([], [other_artifact.id], [pending.id]):
        with pytest.raises(capability_registry.CapabilityError):
            capability_registry.verify_from_run(
                db_session,
                "node-http",
                project_id=1,
                verification_run_id=run.id,
                artifact_ids=args,
                platforms=["linux"],
            )


def test_verify_rejects_cross_project_run(db_session):
    _manifest(db_session)
    _project(db_session, 2)
    foreign = TestRun(project_id=2, run_key="CAP-FOREIGN", status="COMPLETED", outcome="PASS")
    db_session.add(foreign)
    db_session.flush()
    artifact = _artifact(db_session, foreign)
    with pytest.raises(capability_registry.CapabilityError):
        capability_registry.verify_from_run(
            db_session,
            "node-http",
            project_id=1,
            verification_run_id=foreign.id,
            artifact_ids=[artifact.id],
            platforms=["linux"],
        )


def test_runner_image_digest_change_invalidates_verification(db_session):
    _manifest(db_session)
    run = _run(db_session, key="CAP-INV")
    artifact = _artifact(db_session, run)
    capability_registry.verify_from_run(
        db_session,
        "node-http",
        project_id=1,
        verification_run_id=run.id,
        artifact_ids=[artifact.id],
        platforms=["linux"],
        runner_image_digest="sha256:" + "1" * 64,
    )
    row = capability_registry.register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://initial",
        runner_version="1.0.0",
        runner_image_digest="sha256:" + "2" * 64,
    )
    assert row.verified_at is None
    assert row.capability_status == "AVAILABLE"


def test_production_preflight_rejects_available_capability(db_session):
    _manifest(db_session)
    blocked = preflight_graph(
        db_session, GRAPH, allow_available_capability=False
    )
    assert blocked.ok is False
    assert any(issue.code == "CAPABILITY_NOT_VERIFIED" for issue in blocked.issues)

    allowed = preflight_graph(db_session, GRAPH, allow_available_capability=True)
    assert not any(issue.code == "CAPABILITY_NOT_VERIFIED" for issue in allowed.issues)


def test_verified_capability_passes_production_preflight(db_session):
    _manifest(db_session)
    run = _run(db_session, key="CAP-VERIFIED")
    artifact = _artifact(db_session, run)
    capability_registry.verify_from_run(
        db_session,
        "node-http",
        project_id=1,
        verification_run_id=run.id,
        artifact_ids=[artifact.id],
        platforms=["linux"],
    )
    report = preflight_graph(db_session, GRAPH, allow_available_capability=False)
    assert not any(issue.code == "CAPABILITY_NOT_VERIFIED" for issue in report.issues)


def test_manifest_cannot_self_declare_verified(db_session):
    row = _manifest(db_session)
    # register_manifest 没有 status 入参；新注册只能是 REGISTERED/AVAILABLE。
    assert row.capability_status in {"REGISTERED", "AVAILABLE"}
    rows = list(db_session.scalars(select(NodeCapabilityManifest)))
    assert rows and rows[0].verification_run_id is None
