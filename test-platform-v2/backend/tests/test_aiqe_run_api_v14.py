"""v1.4：Run Launch API / Nodes / Assertions 端点测试。"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import (
    NodeRun,
    RunAssertionResult,
    StepAttempt,
    TestRun,
)
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.execution_job import ExecutionJob
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

BASE = "/api/v1/aiqe/runs"

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "health",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/health", "expected_status": 200},
            "outputs": {"ok": "$.json.ok"},
            "assertions": [
                {
                    "assertion_key": "ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-HEALTH",
                    "type": "jsonpath",
                    "path": "$.ok",
                    "expected": True,
                }
            ],
        }
    ],
    "edges": [],
}


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="run-api", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="run-api", name="Run API", owner_id=1, status=1)
    db.add_all([user, project])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    register_manifest(
        db,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    workflow = create_workflow(db, project_id=1, graph=GRAPH)
    approve_workflow(db, workflow.id, approved_by=1)
    db.commit()
    db.info["workflow_id"] = workflow.id


def _make_client(db: Session, permissions: list[str]) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db() -> Iterator[Session]:
        yield db

    def _current_user() -> CurrentUser:
        return CurrentUser(
            user=db.get(User, 1),
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(db_session, ["menu:aiqe_runs", "execution:manage", "defect:list"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


def test_create_run_via_api(api: TestClient, db_session: Session) -> None:
    resp = api.post(
        BASE,
        json={
            "workflow_definition_id": db_session.info["workflow_id"],
            "launch_key": "api-launch-1",
            "build_ref": "b1",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["run"]["status"] == "RUNNING"
    assert data["preflight"]["ok"] is True
    assert data["node_count"] == 1
    run = db_session.get(TestRun, data["run"]["id"])
    assert run.launch_key == "api-launch-1"
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "READY"
    assert db_session.get(ExecutionJob, node.execution_job_id) is not None


def test_create_run_idempotent(api: TestClient) -> None:
    body = {
        "workflow_definition_id": db_session_workflow(api),
        "launch_key": "same-api-key",
    }
    first = api.post(BASE, json=body)
    second = api.post(BASE, json=body)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["data"]["run"]["id"] == second.json()["data"]["run"]["id"]


def db_session_workflow(api: TestClient) -> str:
    # 通过 test client 的 app 取不到 db；这里从固定 seed 的 DB 读取由 fixture 注入的 workflow。
    from app.main import app
    from app.core.db import get_db

    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        from app.aiqe.models.workflow import WorkflowDefinition

        return db.scalar(select(WorkflowDefinition)).id
    finally:
        generator.close()


def test_preflight_blocked_run_is_visible(api: TestClient, db_session: Session) -> None:
    from app.aiqe.models.capability import NodeCapabilityManifest

    row = db_session.scalar(select(NodeCapabilityManifest))
    row.available = False
    db_session.commit()
    resp = api.post(
        BASE,
        json={"workflow_definition_id": db_session.info["workflow_id"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["run"]["status"] == "BLOCKED"
    assert data["preflight"]["ok"] is False


def test_nodes_and_assertions_endpoints(api: TestClient, db_session: Session) -> None:
    resp = api.post(
        BASE,
        json={"workflow_definition_id": db_session.info["workflow_id"]},
    )
    run_id = resp.json()["data"]["run"]["id"]
    run = db_session.get(TestRun, run_id)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    attempt = StepAttempt(
        node_run_id=node.id, step_key="health", attempt_no=1, status="PASSED"
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        RunAssertionResult(
            step_attempt_id=attempt.id,
            assertion_key="ok",
            assertion_type="jsonpath",
            oracle_layer="REQ",
            oracle_ref="AC-HEALTH",
            status="PASS",
            severity="P0",
            expected_json=True,
            actual_json=True,
        )
    )
    node.status = "PASSED"
    db_session.commit()

    nodes = api.get(f"{BASE}/{run_id}/nodes")
    assert nodes.status_code == 200
    payload = nodes.json()["data"]
    assert payload["nodes"][0]["node"]["node_key"] == "health"
    assert payload["nodes"][0]["attempts"][0]["assertions"][0]["status"] == "PASS"
    assertions = api.get(f"{BASE}/{run_id}/assertions")
    assert assertions.status_code == 200
    assert assertions.json()["data"]["total"] == 1
    assert assertions.json()["data"]["items"][0]["oracle_ref"] == "AC-HEALTH"


def test_cross_project_workflow_404(api: TestClient, db_session: Session) -> None:
    from app.aiqe.models.workflow import WorkflowDefinition

    workflow = db_session.scalar(select(WorkflowDefinition))
    workflow.project_id = 2
    db_session.commit()
    resp = api.post(
        BASE,
        json={"workflow_definition_id": workflow.id},
    )
    assert resp.status_code == 404
