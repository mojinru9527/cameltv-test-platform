"""AUD-009/010：缺陷修复回归（40 位 SHA / 部署证明 / fingerprint 幂等 / 范围冻结 / 终端同步）。

替换原先接受 7 位短 SHA、且不校验部署证明的旧用例（v1.5 §02 AUD-009/010）。
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.regression_service import record_deployment_attestation
from app.aiqe.services.snapshot_service import ensure_snapshot
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.aiqe.services.regression_terminal import handle_run_terminal
from app.models.defect import Defect, DefectRegression, RunComparisonSnapshot
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

SHA = "a" * 40
OTHER_SHA = "b" * 40


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="reg-tester", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="reg-proj", name="Reg Project", owner_id=1, status=1)
    other = Project(id=2, code="reg-other", name="Other", owner_id=2, status=1)
    db.add_all([user, project, other])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


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
    client = _make_client(db_session, ["menu:aiqe_runs", "defect:list", "defect:update"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


def _defect(db: Session, *, project_id: int = 1, title: str = "直播入口无响应") -> Defect:
    row = Defect(project_id=project_id, title=title, severity="P1", status="open")
    db.add(row)
    db.commit()
    return row


GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "ui",
            "driver": "playwright",
            "depends_on": [],
            "input": {"url": "https://app.test/live"},
            "assertions": [
                {
                    "assertion_key": "live.entry",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-LIVE",
                    "type": "url_contains",
                    "expected": "/live",
                    "severity": "P0",
                }
            ],
        }
    ],
    "edges": [],
}


def _source_run_with_failure(db: Session, *, project_id: int = 1) -> TestRun:
    """source Run：一个 FAILED 节点 + 一条 required FAIL 断言（绑定冻结快照）。"""
    register_manifest(
        db,
        node_id="node-pw",
        driver_key="playwright",
        capabilities=["aiqe:playwright"],
        platforms=["linux"],
        evidence_ref="evidence://node-pw",
    )
    workflow = create_workflow(db, project_id=project_id, graph=GRAPH)
    approve_workflow(db, workflow.id, approved_by=1)
    db.flush()
    snapshot = ensure_snapshot(db, workflow)
    run = TestRun(
        project_id=project_id,
        run_key="RUN-OLD-0001",
        source_type="manual",
        status="COMPLETED",
        outcome="FAIL",
        build_ref="build-1",
        workflow_definition_id=workflow.id,
        workflow_snapshot_id=snapshot.id,
        workflow_checksum=snapshot.checksum_sha256,
    )
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="ui", driver_key="playwright", status="FAILED")
    db.add(node)
    db.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="ui", attempt_no=1, status="FAILED")
    db.add(attempt)
    db.flush()
    db.add(
        RunAssertionResult(
            step_attempt_id=attempt.id,
            assertion_key="live.entry",
            assertion_type="exists",
            status="FAIL",
            required=True,
        )
    )
    db.commit()
    return run


def _attest(db: Session, *, sha: str = SHA, environment_id: int | None = None) -> None:
    record_deployment_attestation(
        db,
        project_id=1,
        environment_id=environment_id,
        commit_sha=sha,
        image_digest="sha256:image",
        source="ci",
        evidence_ref="ci-run-1",
    )
    db.commit()


# ── 1. SHA 与部署证明 ─────────────────────────────────────
def test_short_sha_rejected(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    resp = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions", json={"fixed_sha": "abc1234"}
    )
    assert resp.status_code == 400
    assert "40 位" in resp.text


def test_missing_attestation_blocks(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    resp = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions", json={"fixed_sha": SHA}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "BLOCKED"
    assert data["run"] is None
    assert data["blockers"][0]["code"] == "DEPLOYMENT_ATTESTATION_MISSING"


def test_deployed_sha_mismatch_blocks(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    _attest(db_session, sha=OTHER_SHA)
    resp = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions", json={"fixed_sha": SHA}
    )
    data = resp.json()["data"]
    assert data["status"] == "BLOCKED"
    assert data["blockers"][0]["code"] == "DEPLOYED_SHA_MISMATCH"


# ── 2. 创建 verification Run / 冻结范围 ───────────────────
def test_create_regression_creates_verification_run(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    source = _source_run_with_failure(db_session)
    _attest(db_session)

    resp = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={
            "fixed_sha": SHA,
            "source_run_id": source.id,
            "scope": "DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT",
            "selected_case_ids": ["P0-login", "P2-search"],
            "reason": "fix verified",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] in {"QUEUED", "RUNNING"}
    assert data["deployed_sha"] == SHA
    assert data["run"]["status"] in {"QUEUED", "RUNNING"}
    assert data["run"]["commit_sha"] == SHA
    assert data["run"]["retest_of"] == source.id
    # 强制集合含直接失败节点/断言 + P0；P2 被排除且有 reason
    assert "node:ui" in data["mandatory_case_ids"]
    assert "assertion:live.entry" in data["mandatory_case_ids"]
    assert "P0-login" in data["mandatory_case_ids"]
    assert {"case_id": "P2-search", "reason": "NON_P0_NOT_IN_MANDATORY_SCOPE"} in data["excluded"]

    db_session.expire_all()
    run = db_session.get(TestRun, data["verification_run_id"])
    assert run.source_type == "regression"
    assert run.environment_snapshot_json["scope_hash"] == data["scope_hash"]
    nodes = list(db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    assert [node.node_key for node in nodes] == ["ui"]
    # 旧 Run 不被修改
    assert db_session.get(TestRun, source.id).status == "COMPLETED"


def test_fingerprint_idempotent(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    source = _source_run_with_failure(db_session)
    _attest(db_session)
    payload = {
        "fixed_sha": SHA,
        "scope": "DIRECT_FAILURES",
        "selected_case_ids": [],
        "source_run_id": source.id,
    }
    first = api.post(f"/api/v1/aiqe/defects/{defect.id}/regressions", json=payload)
    second = api.post(f"/api/v1/aiqe/defects/{defect.id}/regressions", json=payload)
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["data"]["created"] is False
    rows = list(db_session.scalars(select(DefectRegression)))
    assert len(rows) == 1
    runs = list(db_session.scalars(select(TestRun).where(TestRun.source_type == "regression")))
    assert len(runs) == 1


def test_different_scope_creates_new_regression(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    _attest(db_session)
    a = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "scope": "DIRECT_FAILURES"},
    ).json()["data"]
    b = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "scope": "DIRECT_FAILURES_PLUS_P0", "selected_case_ids": ["P0-x"]},
    ).json()["data"]
    assert a["id"] != b["id"]


# ── 3. 终端同步 + 对比快照 ────────────────────────────────
def _complete_run(db: Session, run: TestRun, *, assertion_status: str = "PASS") -> None:
    node = db.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.status = "PASSED" if assertion_status == "PASS" else "FAILED"
    attempt = db.scalar(select(StepAttempt).where(StepAttempt.node_run_id == node.id))
    if attempt is None:
        attempt = StepAttempt(
            node_run_id=node.id, step_key=node.node_key, attempt_no=1, status=node.status
        )
        db.add(attempt)
        db.flush()
    attempt.status = node.status
    row = db.scalar(
        select(RunAssertionResult).where(RunAssertionResult.step_attempt_id == attempt.id)
    )
    if row is None:
        row = RunAssertionResult(
            step_attempt_id=attempt.id,
            assertion_key="live.entry",
            assertion_type="exists",
            required=True,
        )
        db.add(row)
    row.status = assertion_status
    run.status = "COMPLETED"
    run.outcome = "PASS" if assertion_status == "PASS" else "FAIL"
    run.finished_at = datetime.now(UTC)
    db.commit()


def test_terminal_sync_pass_and_comparison(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    source = _source_run_with_failure(db_session)
    _attest(db_session)
    created = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "source_run_id": source.id},
    ).json()["data"]
    run = db_session.get(TestRun, created["verification_run_id"])
    _complete_run(db_session, run, assertion_status="PASS")

    result = handle_run_terminal(db_session, run_id=run.id)
    db_session.commit()
    assert result.status == "PASS"
    assert result.suggestion == "READY_FOR_HUMAN_CLOSE"

    again = handle_run_terminal(db_session, run_id=run.id)
    assert again.skipped is True and again.reason == "ALREADY_HANDLED"

    db_session.expire_all()
    regression = db_session.get(DefectRegression, created["id"])
    assert regression.status == "PASS"
    assert regression.completed_at is not None
    assert regression.comparison_snapshot_id
    snapshot = db_session.get(RunComparisonSnapshot, regression.comparison_snapshot_id)
    assert snapshot.outcome == "PASS"
    assert "ui:live.entry" in snapshot.assertion_diff_json["fixed_failures"]
    # 绝不自动关闭缺陷
    assert db_session.get(Defect, defect.id).status == "open"

    resp = api.get(f"/api/v1/aiqe/regressions/{created['id']}/comparison")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["available"] is True
    assert data["snapshot"]["outcome"] == "PASS"
    assert data["suggestion"] == "READY_FOR_HUMAN_CLOSE"


def test_terminal_sync_fail_needs_more_fix(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    source = _source_run_with_failure(db_session)
    _attest(db_session)
    created = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "source_run_id": source.id},
    ).json()["data"]
    run = db_session.get(TestRun, created["verification_run_id"])
    _complete_run(db_session, run, assertion_status="FAIL")

    result = handle_run_terminal(db_session, run_id=run.id)
    db_session.commit()
    assert result.status == "FAIL"
    assert result.suggestion == "NEEDS_MORE_FIX"


def test_terminal_sync_without_assertions_is_unknown(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    source = _source_run_with_failure(db_session)
    _attest(db_session)
    created = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "scope": "DIRECT_FAILURES", "source_run_id": source.id},
    ).json()["data"]
    run = db_session.get(TestRun, created["verification_run_id"])
    run.status = "COMPLETED"
    run.outcome = "PASS"
    db_session.commit()

    result = handle_run_terminal(db_session, run_id=run.id)
    assert result.status == "UNKNOWN"


# ── 4. 取消 / 权限 / 404 / 项目隔离 ───────────────────────
def test_cancel_regression(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    _attest(db_session)
    created = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions", json={"fixed_sha": SHA}
    ).json()["data"]
    resp = api.post(f"/api/v1/aiqe/regressions/{created['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELLED"
    assert api.post(f"/api/v1/aiqe/regressions/{created['id']}/cancel").status_code == 400


def test_invalid_defect_rejected(api: TestClient) -> None:
    resp = api.post("/api/v1/aiqe/defects/999/regressions", json={"fixed_sha": SHA})
    assert resp.status_code == 400


def test_cross_project_source_run_rejected(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    foreign = _source_run_with_failure(db_session, project_id=2)
    resp = api.post(
        f"/api/v1/aiqe/defects/{defect.id}/regressions",
        json={"fixed_sha": SHA, "source_run_id": foreign.id},
    )
    assert resp.status_code == 400


def test_regression_requires_console_permission(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:list", "defect:update"])
    try:
        resp = client.post("/api/v1/aiqe/defects/1/regressions", json={"fixed_sha": SHA})
        assert resp.status_code == 403
    finally:
        from app.main import app

        app.dependency_overrides.clear()


def test_unknown_regression_404(api: TestClient) -> None:
    assert api.get("/api/v1/aiqe/regressions/424242").status_code == 404
    assert api.get("/api/v1/aiqe/regressions/424242/comparison").status_code == 404
