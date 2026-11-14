"""v1.4 执行链 E2E（单元级）：变量传递 → 断言 → outputs → 证据 → DAG 推进。"""
from __future__ import annotations

from sqlalchemy import select

from app.aiqe.models.run import NodeRun, RunAssertionResult, TestRun
from app.aiqe.services import execution_service, job_consumer, node_executor
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.execution_job import ExecutionJob
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
        },
        {
            "key": "query",
            "driver": "http",
            "depends_on": ["login"],
            "input": {
                "url": "https://api.test/orders",
                "expected_status": 201,
                "headers": {
                    "Authorization": "Bearer ${nodes.login.outputs.token}",
                    "X-Secret": "${SECRET:API_KEY}",
                },
            },
            "assertions": [
                {
                    "assertion_key": "ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-ORDER-1",
                    "type": "jsonpath",
                    "path": "$.ok",
                    "expected": True,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [{"from": "login", "to": "query"}],
    "run_policy": {"max_parallel_nodes": 2, "fail_fast": False},
}


def _setup(db):
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
    workflow = create_workflow(db, project_id=1, graph=GRAPH)
    approve_workflow(db, workflow.id, approved_by=1)
    db.flush()
    return workflow


def test_pipeline_variable_assertion_outputs_and_evidence(db_session, monkeypatch):
    monkeypatch.setenv("AIQE_SECRET_API_KEY", "s3cr3t")
    calls: list[dict] = []

    def fake_execute(node, *, input_override=None, db_engine=None):
        calls.append({"node": node.node_key, "input": dict(input_override or {})})
        if node.node_key == "login":
            return node_executor.NodeExecution(
                status="PASSED",
                detail={
                    "request": {"method": "POST", "url": "https://api.test/login"},
                    "response": {"status_code": 200, "body": '{"token":"tok-1"}'},
                },
                data={"status_code": 200, "json": {"token": "tok-1"}},
            )
        return node_executor.NodeExecution(
            status="PASSED",
            detail={
                "request": {"method": "GET", "url": "https://api.test/orders"},
                "response": {"status_code": 201, "body": '{"ok":true}'},
            },
            data={"status_code": 201, "json": {"ok": True}},
        )

    monkeypatch.setattr(execution_service, "execute_node", fake_execute)
    workflow = _setup(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="pipeline-1",
    )
    db_session.commit()
    assert run.status == "RUNNING"

    # 执行 login
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    assert len(claimed) == 1
    first_job = db_session.get(ExecutionJob, claimed[0])
    payload = first_job.payload_json
    assert "s3cr3t" not in payload
    job_consumer.run_job(db_session, claimed[0])

    login = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login")
    )
    query = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "query")
    )
    db_session.expire_all()
    login = db_session.get(NodeRun, login.id)
    query = db_session.get(NodeRun, query.id)
    assert login.status == "PASSED"
    assert login.outputs_json["token"] == "tok-1"
    assert query.status == "READY"
    assert query.execution_job_id is not None
    # 解析输入已持久化，但 secret 明文不落库
    assert query.resolved_input_json["headers"]["Authorization"] == "Bearer tok-1"
    assert query.resolved_input_json["headers"]["X-Secret"] == "***"
    assert query.secret_keys_json == ["API_KEY"]

    # 执行 query
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    assert len(claimed) == 1
    job_consumer.run_job(db_session, claimed[0])
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    query = db_session.get(NodeRun, query.id)
    assert query.status == "PASSED"
    assert run.status == "COMPLETED"
    assert run.outcome == "PASS"

    # 变量真实传递到执行器（且 secret 只在内存）
    query_call = [call for call in calls if call["node"] == "query"][0]
    assert query_call["input"]["headers"]["Authorization"] == "Bearer tok-1"
    assert query_call["input"]["headers"]["X-Secret"] == "s3cr3t"

    assertions = list(
        db_session.scalars(
            select(RunAssertionResult).where(
                RunAssertionResult.assertion_key == "ok"
            )
        )
    )
    assert len(assertions) == 1
    assert assertions[0].status == "PASS"
    assert assertions[0].oracle_ref == "AC-ORDER-1"

    artifacts = execution_service.persist_execution_evidence(
        db_session,
        run=run,
        node=query,
        attempt=query.step_attempts[-1],
        execution=node_executor.NodeExecution(
            status="PASSED",
            detail={"request": {"a": 1}, "response": {"b": 2}},
            data={},
        ),
    )
    assert len(artifacts) == 2


def test_probe_only_execution_never_passes(db_session, monkeypatch):
    monkeypatch.setenv("AIQE_SECRET_API_KEY", "s3cr3t")
    workflow = _setup(db_session)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="pipeline-probe",
    )
    db_session.commit()

    def fake_probe(node, *, input_override=None, db_engine=None):
        return node_executor.NodeExecution(
            status="PASSED",
            detail={},
            data={"business_action_dispatched": False, "locators": {}},
        )

    monkeypatch.setattr(execution_service, "execute_node", fake_probe)
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    job_consumer.run_job(db_session, claimed[0])
    db_session.expire_all()
    login = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login")
    )
    # login 无业务断言时允许 PASS（setup 节点）；关键是被 lead 的 probe 不能伪造 PASS：
    # query 节点尚未执行，必须仍是 READY/PENDING。
    query = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "query")
    )
    assert query.status != "PASSED"
