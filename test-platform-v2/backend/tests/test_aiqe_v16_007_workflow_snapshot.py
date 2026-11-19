"""V16-007 验收：不可变 Workflow 快照与完整 DAG 克隆。

覆盖规格：
- 执行只能绑定 content-addressed 不可变 WorkflowSnapshot；
- 快照 hash 可复算、不可修改、按 Project 隔离；
- SnapshotCloner 完整保留 depends_on/edges/assertions/outputs/条件；
- 克隆可移除实验目标节点并重写依赖，不产生悬挂/环路；
- graph_override 也必须落为快照。
"""
from __future__ import annotations

import copy

import pytest
from sqlalchemy import select

from app.aiqe.models.run import TestRun
from app.aiqe.models.workflow import WorkflowSnapshot
from app.aiqe.services import snapshot_service
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import LaunchError, launch, launch_run
from app.aiqe.services.snapshot_service import (
    SnapshotError,
    canonical_json,
    checksum_of,
    clone_graph,
    clone_snapshot,
    ensure_snapshot,
    get_snapshot,
    snapshot_graph,
)
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
            "outputs": {"token": "$.json.token"},
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
            "key": "create_order",
            "driver": "http",
            "depends_on": ["login"],
            "input": {
                "url": "https://api.test/orders",
                "headers": {"Authorization": "Bearer ${nodes.login.outputs.token}"},
                "expected_status": 201,
            },
            "outputs": {"order_id": "$.json.id"},
            "assertions": [
                {
                    "assertion_key": "order_created",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-ORDER",
                    "type": "http_status",
                    "expected": 201,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "verify_public",
            "driver": "http",
            "depends_on": ["create_order"],
            "input": {"url": "https://api.test/public", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "public_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-PUBLIC",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [
        {"from": "login", "to": "create_order"},
        {"from": "create_order", "to": "verify_public"},
    ],
    "run_policy": {"max_parallel_nodes": 2},
}


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


# ── 1. content-addressed 快照 ──────────────────────────────
def test_snapshot_is_content_addressed_and_immutable(db_session):
    workflow = _workflow(db_session)
    first = ensure_snapshot(db_session, workflow)
    second = ensure_snapshot(db_session, workflow)
    assert first.id == second.id
    assert first.checksum_sha256 == checksum_of(GRAPH)
    assert first.checksum_sha256 == snapshot_service.checksum_of(first.canonical_json)

    # 修改 Workflow 定义（新版本/新内容）后旧快照完全不变
    old_snapshot_json = canonical_json(first.canonical_json)
    workflow.graph_json = copy.deepcopy(GRAPH)
    workflow.graph_json["nodes"][0]["input"]["url"] = "https://api.test/login-v2"
    db_session.commit()
    updated = ensure_snapshot(db_session, workflow)
    assert updated.id != first.id
    db_session.refresh(first)
    assert canonical_json(first.canonical_json) == old_snapshot_json
    assert first.checksum_sha256 != updated.checksum_sha256


def test_snapshot_is_project_scoped(db_session):
    workflow = _workflow(db_session)
    snapshot = ensure_snapshot(db_session, workflow)
    with pytest.raises(SnapshotError):
        get_snapshot(db_session, snapshot.id, project_id=99)


# ── 2. 克隆保留全部 DAG 语义 ───────────────────────────────
def test_clone_graph_preserves_dependencies_edges_assertions_outputs():
    clone = clone_graph(GRAPH, remove_node_keys=("verify_public",))
    keys = [node["key"] for node in clone["nodes"]]
    assert keys == ["login", "create_order"]
    create = next(node for node in clone["nodes"] if node["key"] == "create_order")
    assert create["depends_on"] == ["login"]  # 不硬编码空依赖
    assert create["assertions"] and create["outputs"]
    assert clone["edges"] == [{"from": "login", "to": "create_order"}]
    assert clone["run_policy"] == GRAPH["run_policy"]


def test_clone_removing_dependency_rewrites_edges():
    clone = clone_graph(GRAPH, remove_node_keys=("create_order",))
    verify = next(node for node in clone["nodes"] if node["key"] == "verify_public")
    # 中间节点被移除后，下游依赖被重写而不是悬挂
    assert verify["depends_on"] == []
    assert clone["edges"] == []
    snapshot_service.validate_graph(clone)


def test_clone_snapshot_creates_child_and_validates(db_session):
    workflow = _workflow(db_session)
    parent = ensure_snapshot(db_session, workflow)
    same = clone_snapshot(db_session, parent, execution_kind="DEFECT_REGRESSION")
    assert same.id == parent.id  # 内容相同 → 复用（不可变、content-addressed）

    child = clone_snapshot(
        db_session,
        parent,
        execution_kind="DEFECT_REGRESSION",
        remove_node_keys=("verify_public",),
    )
    assert child.id != parent.id
    assert child.parent_snapshot_id == parent.id
    assert child.execution_kind == "DEFECT_REGRESSION"
    assert child.checksum_sha256 == checksum_of(child.canonical_json)
    assert snapshot_graph(child)["edges"] == [{"from": "login", "to": "create_order"}]

    with pytest.raises(SnapshotError):
        clone_snapshot(
            db_session,
            parent,
            execution_kind="DEFECT_REGRESSION",
            remove_node_keys=("login", "create_order", "verify_public"),
        )


# ── 3. Launch 绑定快照 ─────────────────────────────────────
def test_launch_binds_immutable_snapshot(db_session):
    workflow = _workflow(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="v16-007-1",
    )
    db_session.commit()
    assert run.workflow_snapshot_id
    snapshot = get_snapshot(db_session, run.workflow_snapshot_id, project_id=1)
    assert run.workflow_checksum == snapshot.checksum_sha256
    assert run.workflow_snapshot_json == snapshot.canonical_json
    assert run.execution_kind == "NORMAL"

    result = launch(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="v16-007-2",
    )
    assert result.run_id
    assert result.snapshot_id
    assert result.snapshot_hash == snapshot.checksum_sha256
    assert result.job_ids  # 正式入口必须真实派发 Job
    assert result.dispatch_status in {"DISPATCHED", "BLOCKED"}


def test_launch_with_snapshot_rejects_checksum_mismatch(db_session):
    workflow = _workflow(db_session)
    snapshot = ensure_snapshot(db_session, workflow)
    with pytest.raises(LaunchError) as exc:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_snapshot_id=snapshot.id,
            expected_checksum="0" * 64,
            launch_key="v16-007-3",
        )
    assert exc.value.code == "WORKFLOW_CHECKSUM_MISMATCH"


def test_launch_with_cloned_snapshot_uses_clone_graph(db_session):
    workflow = _workflow(db_session)
    parent = ensure_snapshot(db_session, workflow)
    child = clone_snapshot(db_session, parent, execution_kind="DEFECT_REGRESSION")
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_snapshot_id=child.id,
        execution_kind="DEFECT_REGRESSION",
        launch_key="v16-007-4",
    )
    db_session.commit()
    assert run.workflow_snapshot_id == child.id
    assert run.execution_kind == "DEFECT_REGRESSION"
    assert run.workflow_checksum == child.checksum_sha256


def test_graph_override_is_frozen_into_snapshot(db_session):
    _project(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        graph_override=GRAPH,
        launch_key="v16-007-5",
    )
    db_session.commit()
    assert run.workflow_snapshot_id
    snapshot = get_snapshot(db_session, run.workflow_snapshot_id, project_id=1)
    assert snapshot.workflow_id is None
    assert snapshot.checksum_sha256 == checksum_of(GRAPH)
    assert run.workflow_checksum == snapshot.checksum_sha256


# ── 4. 篡改检测 ────────────────────────────────────────────
def test_snapshot_hash_detects_tampering(db_session):
    workflow = _workflow(db_session)
    snapshot = ensure_snapshot(db_session, workflow)
    tampered = copy.deepcopy(snapshot.canonical_json)
    tampered["nodes"][0]["input"]["url"] = "https://evil.test"
    assert checksum_of(tampered) != snapshot.checksum_sha256
    assert checksum_of(snapshot.canonical_json) == snapshot.checksum_sha256
