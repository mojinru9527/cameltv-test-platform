"""V16-008 验收：Defect Regression Mandatory Scope 真正执行。

覆盖规格：
- Scope 由服务端计算并冻结（scope_id/规则版本/输入 refs/必测集合/原因/审批人/checksum）；
- mandatory/related/smoke 三类集合 + 不允许排除 mandatory；
- 必测节点缺失或无失败证据 → BLOCKED，不得缩小范围后 PASS；
- Launch 必须携带 Scope Snapshot，mandatory 必须存在于执行 DAG；
- Run PASS 要求全部 mandatory PASSED。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.defect import Defect
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import dag_scheduler
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.regression_scope import (
    ScopeError,
    build_scope_plan,
    ensure_scope_snapshot,
    verify_scope_snapshot,
)
from app.aiqe.services.regression_service import (
    create_regression_request,
    record_deployment_attestation,
)
from app.aiqe.services.run_launch import LaunchError, launch, launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.project import Project

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "login",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/login", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "login_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-LOGIN",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "order",
            "driver": "http",
            "depends_on": ["login"],
            "input": {"url": "https://api.test/orders", "expected_status": 201},
            "assertions": [
                {
                    "assertion_key": "order_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-ORDER",
                    "type": "http_status",
                    "expected": 201,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "verify",
            "driver": "http",
            "depends_on": ["order"],
            "input": {"url": "https://api.test/state", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "verify_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-VERIFY",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "unrelated",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/other", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "other_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-OTHER",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [
        {"from": "login", "to": "order"},
        {"from": "order", "to": "verify"},
    ],
}

SHA = "c" * 40


def _project(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="TEST", name="Test", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )


def _workflow(db):
    _project(db)
    row = create_workflow(db, project_id=1, graph=GRAPH)
    approve_workflow(db, row.id, approved_by=1)
    db.flush()
    return row


def _source_run(db) -> TestRun:
    workflow = _workflow(db)
    result = launch(
        db,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="v16-008-src",
    )
    node = db.scalar(select(NodeRun).where(NodeRun.run_id == result.run_id))
    node.status = "FAILED"
    node.error_class = "ASSERTION_FAILED"
    db.commit()
    return db.get(TestRun, result.run_id)


# ── 1. Scope 计算：三类集合 + checksum + 原因 ──────────────
def test_scope_plan_builds_mandatory_related_smoke_and_checksum(db_session):
    plan = build_scope_plan(
        scope="DIRECT_FAILURES",
        graph=GRAPH,
        mandatory_refs=["node:order", "assertion:login_ok", "P0-login"],
        excluded=[{"case_id": "P2-x", "reason": "NON_P0_NOT_IN_MANDATORY_SCOPE"}],
        inputs={"source_run_id": "r1", "fixed_sha": SHA},
    )
    assert plan["mandatory_node_keys"] == ["login", "order"]
    assert plan["related_node_keys"] == []  # login 已是 mandatory
    assert plan["smoke_node_keys"] == ["unrelated", "verify"]
    assert plan["reasons"]["order"] == "MANDATORY_FAILED_OR_P0"
    assert plan["reasons"]["unrelated"] == "REGRESSION_SMOKE"
    assert len(plan["checksum_sha256"]) == 64
    # 相同输入 checksum 稳定
    again = build_scope_plan(
        scope="DIRECT_FAILURES",
        graph=GRAPH,
        mandatory_refs=["node:order", "assertion:login_ok", "P0-login"],
        excluded=[{"case_id": "P2-x", "reason": "NON_P0_NOT_IN_MANDATORY_SCOPE"}],
        inputs={"source_run_id": "r1", "fixed_sha": SHA},
    )
    assert again["checksum_sha256"] == plan["checksum_sha256"]


def test_scope_plan_rejects_missing_mandatory_and_empty_scope():
    with pytest.raises(ScopeError) as exc:
        build_scope_plan(
            scope="DIRECT_FAILURES",
            graph=GRAPH,
            mandatory_refs=["node:ghost"],
            excluded=[],
            inputs={},
        )
    assert exc.value.code == "MANDATORY_NODE_MISSING"

    with pytest.raises(ScopeError) as exc2:
        build_scope_plan(
            scope="DIRECT_FAILURES",
            graph=GRAPH,
            mandatory_refs=["P0-case-only"],
            excluded=[],
            inputs={},
        )
    assert exc2.value.code == "MANDATORY_SCOPE_EMPTY"


def test_scope_snapshot_is_immutable_and_tamper_evident(db_session):
    plan = build_scope_plan(
        scope="DIRECT_FAILURES",
        graph=GRAPH,
        mandatory_refs=["node:order"],
        excluded=[],
        inputs={"source_run_id": "r1"},
    )
    row = ensure_scope_snapshot(db_session, project_id=1, defect_id=1, plan=plan)
    db_session.commit()
    verified = verify_scope_snapshot(row, GRAPH)
    assert verified["checksum_sha256"] == plan["checksum_sha256"]

    # 篡改 mandatory 集合 → checksum 不匹配
    row.mandatory_node_keys_json = ["order", "unrelated"]
    with pytest.raises(ScopeError) as exc:
        verify_scope_snapshot(row, GRAPH)
    assert exc.value.code == "SCOPE_CHECKSUM_MISMATCH"


# ── 2. Regression：scope 冻结并绑定 Run ───────────────────
def test_regression_freezes_scope_snapshot_and_binds_run(db_session):
    _project(db_session)
    source = _source_run(db_session)
    defect = Defect(project_id=1, defect_id="BUG-8", title="x", severity="P1", status="open")
    db_session.add(defect)
    db_session.flush()
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=SHA, source="ci"
    )
    db_session.commit()

    row, run, created = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=SHA,
        source_run_id=source.id,
        idempotency_key="v16-008-1",
    )
    db_session.commit()
    assert created is True and run is not None
    assert row.scope_snapshot_id
    assert row.scope_hash and len(row.scope_hash) == 64
    from app.aiqe.models.regression_scope import RegressionScopeSnapshot

    scope_row = db_session.get(RegressionScopeSnapshot, row.scope_snapshot_id)
    assert scope_row is not None
    assert scope_row.mandatory_node_keys_json == ["login"]  # 失败节点是首波 login
    assert scope_row.rule_version == "V16-008.1"
    assert scope_row.inputs_json["snapshot_hash"] == run.workflow_checksum

    env_scope = run.environment_snapshot_json["scope_snapshot"]
    assert env_scope["checksum_sha256"] == scope_row.checksum_sha256
    assert env_scope["mandatory_node_keys"] == ["login"]
    assert len(run.environment_snapshot_json["scope_snapshot_id"]) == 36


def test_regression_without_failure_evidence_is_blocked(db_session):
    _project(db_session)
    workflow = _workflow(db_session)
    clean = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-008-clean",
    )
    db_session.commit()
    defect = Defect(project_id=1, defect_id="BUG-9", title="x", severity="P2", status="open")
    db_session.add(defect)
    db_session.flush()
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=SHA, source="ci"
    )
    db_session.commit()

    row, run, created = create_regression_request(
        db_session, project_id=1, defect_id=defect.id, fixed_sha=SHA,
        source_run_id=clean.run_id, idempotency_key="v16-008-2",
    )
    db_session.commit()
    assert created is True
    assert run is None
    assert row.status == "BLOCKED"
    assert any(
        item["code"] == "MANDATORY_SCOPE_EMPTY" for item in (row.blockers_json or [])
    )


def test_different_sha_or_environment_creates_new_regression(db_session):
    _project(db_session)
    source = _source_run(db_session)
    defect = Defect(project_id=1, defect_id="BUG-10", title="x", severity="P1", status="open")
    db_session.add(defect)
    db_session.flush()
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=SHA, source="ci"
    )
    db_session.commit()
    first, _run1, created1 = create_regression_request(
        db_session, project_id=1, defect_id=defect.id, fixed_sha=SHA,
        source_run_id=source.id, idempotency_key="k1",
    )
    db_session.commit()
    # 相同输入幂等
    again, _run2, created2 = create_regression_request(
        db_session, project_id=1, defect_id=defect.id, fixed_sha=SHA,
        source_run_id=source.id, idempotency_key="k1",
    )
    assert created1 is True and created2 is False and again.id == first.id

    other_sha = "d" * 40
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=other_sha, source="ci"
    )
    db_session.commit()
    second, _run3, created3 = create_regression_request(
        db_session, project_id=1, defect_id=defect.id, fixed_sha=other_sha,
        source_run_id=source.id, idempotency_key="k2",
    )
    db_session.commit()
    assert created3 is True
    assert second.id != first.id


# ── 3. Launch 强制携带 scope，且不得排除 mandatory ─────────
def test_launch_requires_scope_snapshot_for_regression(db_session):
    workflow = _workflow(db_session)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=workflow.id,
            execution_kind="DEFECT_REGRESSION",
            launch_key="v16-008-no-scope",
        )
    assert exc.value.code == "SCOPE_SNAPSHOT_REQUIRED"


def test_launch_rejects_scope_with_missing_mandatory(db_session):
    workflow = _workflow(db_session)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=workflow.id,
            execution_kind="DEFECT_REGRESSION",
            scope_snapshot={"mandatory_node_keys": ["ghost"], "checksum_sha256": "0" * 64},
            launch_key="v16-008-bad-scope",
        )
    assert exc.value.code == "MANDATORY_SCOPE_VIOLATION"


# ── 4. Run PASS 门禁：mandatory 必须全 PASSED ─────────────
def _gate_run(db, statuses: dict[str, str], *, mandatory: list[str]) -> TestRun:
    _project(db)
    workflow = _workflow(db)
    graph = dict(workflow.graph_json)
    run = TestRun(
        project_id=1,
        run_key=f"RUN-GATE-{len(statuses)}-{mandatory[0]}",
        status="RUNNING",
        environment_snapshot_json={"scope_snapshot": {"mandatory_node_keys": mandatory}},
        workflow_snapshot_json=graph,
    )
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    for row in rows:
        row.status = statuses.get(row.node_key, "PASSED")
    db.commit()
    return run


def _assertion_rows(db, run) -> None:
    """为每个节点补一条 required PASS 断言，验证 mandatory 门禁独立生效。"""
    from app.aiqe.models.run import RunAssertionResult, StepAttempt

    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    for node in rows:
        attempt = StepAttempt(node_run_id=node.id, step_key=node.node_key, attempt_no=1, status="PASSED")
        db.add(attempt)
        db.flush()
        db.add(
            RunAssertionResult(
                step_attempt_id=attempt.id,
                assertion_key=f"{node.node_key}-a",
                assertion_type="http_status",
                oracle_layer="REQ",
                status="PASS",
                severity="P0",
                required=True,
            )
        )
    db.commit()


def test_mandatory_failed_never_passes(db_session):
    run = _gate_run(db_session, {"login": "FAILED"}, mandatory=["login"])
    _assertion_rows(db_session, run)
    rows = list(db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    dag_scheduler._finalize(db_session, run, rows, run.workflow_snapshot_json)
    db_session.commit()
    assert run.outcome == "FAIL"


def test_mandatory_blocked_is_incomplete(db_session):
    run = _gate_run(db_session, {"login": "BLOCKED"}, mandatory=["login"])
    _assertion_rows(db_session, run)
    rows = list(db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    dag_scheduler._finalize(db_session, run, rows, run.workflow_snapshot_json)
    db_session.commit()
    assert run.outcome == "INCOMPLETE"


def test_mandatory_missing_from_execution_is_incomplete(db_session):
    run = _gate_run(db_session, {}, mandatory=["ghost"])
    _assertion_rows(db_session, run)
    rows = list(db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    dag_scheduler._finalize(db_session, run, rows, run.workflow_snapshot_json)
    db_session.commit()
    assert run.outcome == "INCOMPLETE"
