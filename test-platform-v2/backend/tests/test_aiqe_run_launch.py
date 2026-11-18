"""v1.4 FIX-005/006：Capability Preflight + Run Launch 验收测试。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.preflight import preflight_graph
from app.aiqe.services.run_launch import (
    LaunchError,
    cancel_run,
    launch_run,
)
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.environment import Environment
from app.models.execution_job import ExecutionJob
from app.models.project import Project


def _project(db):
    project = db.get(Project, 1)
    if project is None:
        project = Project(id=1, code="TEST", name="Test", owner_id=1, status=1)
        db.add(project)
        db.flush()
    return project


GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "health",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/health", "expected_status": 200},
            "assertions": [
                {
                    "key": "status",
                    "oracle_layer": "STD",
                    "oracle_ref": "STD-HEALTH-200",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        }
    ],
    "edges": [],
    "run_policy": {"max_parallel_nodes": 1},
}


def _workflow(db, graph=None):
    _project(db)
    row = create_workflow(db, project_id=1, graph=graph or GRAPH)
    approve_workflow(db, row.id, approved_by=1)
    db.flush()
    return row


def test_preflight_no_manifest_blocks(db_session):
    report = preflight_graph(db_session, GRAPH, inprocess_enabled=False)
    assert report.ok is False
    assert report.issues[0].code == "CAPABILITY_UNAVAILABLE"
    assert report.issues[0].required_capability


def test_preflight_available_manifest_passes(db_session):
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    report = preflight_graph(db_session, GRAPH, inprocess_enabled=False)
    assert report.ok is True


def test_preflight_offline_manifest_blocks(db_session):
    row = register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
    db_session.flush()
    report = preflight_graph(db_session, GRAPH, inprocess_enabled=False)
    assert report.ok is False
    assert report.issues[0].code == "CAPABILITY_UNAVAILABLE"


def test_preflight_inprocess_http_fallback(db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "aiqe_inprocess_executor_enabled", True)
    report = preflight_graph(db_session, GRAPH, inprocess_enabled=True)
    assert report.ok is True


def test_launch_requires_approved_workflow(db_session):
    _project(db_session)
    row = create_workflow(db_session, project_id=1, graph=GRAPH)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=row.id,
        )
    assert exc.value.code == "WORKFLOW_NOT_APPROVED"


def test_launch_rejects_checksum_mismatch(db_session):
    row = _workflow(db_session)
    row.graph_json = {**GRAPH, "run_policy": {"max_parallel_nodes": 2}}
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=row.id,
        )
    assert exc.value.code == "WORKFLOW_CHECKSUM_MISMATCH"


def test_launch_blocked_when_preflight_fails(db_session):
    row = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        launch_key="blocked-1",
    )
    assert run.status == "BLOCKED"
    assert run.preflight_json["ok"] is False
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert node.error_class == "CAPABILITY_UNAVAILABLE"
    assert db_session.scalar(select(ExecutionJob)) is None


def test_launch_creates_nodes_and_dispatches_job(db_session):
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        launch_key="launch-1",
        build_ref="build-1",
        commit_sha="abcdef1",
    )
    assert run.status == "RUNNING"
    assert run.workflow_checksum == row.checksum
    assert run.workflow_snapshot_json["nodes"][0]["key"] == "health"
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "READY"
    assert node.execution_job_id is not None
    job = db_session.get(ExecutionJob, node.execution_job_id)
    assert job.status == "pending"
    assert job.payload_json
    events = [event.event_type for event in run_events(db_session, run.id)]
    assert "run.created" in events and "job.dispatched" in events


def test_launch_key_is_idempotent(db_session):
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    first = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        launch_key="same-key",
    )
    second = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        launch_key="same-key",
    )
    assert second.id == first.id
    assert len(list(db_session.scalars(select(TestRun)))) == 1
    assert len(list(db_session.scalars(select(ExecutionJob)))) == 1


def test_production_run_creation_disabled(db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "aiqe_prod_run_create_enabled", False)
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=row.id,
        )
    assert exc.value.code == "PROD_RUN_CREATE_DISABLED"


def test_production_flag_allows_explicit_enable(db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "aiqe_prod_run_create_enabled", True)
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
    )
    assert run.status == "RUNNING"


def test_environment_is_production_flag_blocks(db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "test")
    env = Environment(project_id=1, name="prod", base_url="https://x", is_production=True)
    db_session.add(env)
    db_session.flush()
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=row.id,
            environment_id=env.id,
        )
    assert exc.value.code == "PROD_RUN_CREATE_DISABLED"


def test_preflight_missing_environment_and_profile(db_session):
    env_report = preflight_graph(
        db_session, GRAPH, project_id=1, environment_id=999, inprocess_enabled=True
    )
    assert any(issue.code == "ENVIRONMENT_MISSING" for issue in env_report.issues)
    profile_report = preflight_graph(
        db_session, GRAPH, project_id=1, profile_id="missing", inprocess_enabled=True
    )
    assert any(issue.code == "PROFILE_MISSING" for issue in profile_report.issues)


def test_preflight_missing_secret_and_fixture(db_session, monkeypatch):
    monkeypatch.delenv("AIQE_SECRET_API_KEY", raising=False)
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "n1",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": "https://api.test/x",
                    "headers": {"X-Key": "${SECRET:API_KEY}"},
                    "user": "${FIXTURE:user}",
                },
            }
        ],
        "edges": [],
    }
    report = preflight_graph(
        db_session, graph, project_id=1, inprocess_enabled=True, fixtures={}
    )
    codes = {issue.code for issue in report.issues}
    assert "SECRET_MISSING" in codes
    assert "FIXTURE_MISSING" in codes


def test_launch_rejects_missing_environment(db_session):
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=row.id,
            environment_id=999,
        )
    assert exc.value.code == "ENVIRONMENT_NOT_FOUND"


def test_launch_never_persists_secret_values(db_session):
    import json

    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        environment_snapshot={"secrets": {"API_KEY": "s3cr3t"}, "env": "test"},
    )
    serialized = json.dumps(run.environment_snapshot_json)
    assert "s3cr3t" not in serialized
    assert run.environment_snapshot_json["secret_keys"] == ["API_KEY"]


def test_cancel_run_releases_pending_jobs(db_session):
    register_manifest(
        db_session,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    row = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=row.id,
        launch_key="cancel-1",
    )
    assert run.status == "RUNNING"
    canceled = cancel_run(db_session, project_id=1, run_id=run.id, user_id=1)
    assert canceled.status == "CANCELED"
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "CANCELED"
    job = db_session.get(ExecutionJob, node.execution_job_id)
    assert job.status == "canceled"
    assert job.finished_at is not None
    with pytest.raises(LaunchError):
        cancel_run(db_session, project_id=1, run_id=run.id, user_id=1)


def run_events(db, run_id):
    from app.aiqe.services.event_service import list_events

    return list_events(db, run_id, limit=100)
