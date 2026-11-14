"""v1.4 FIX-006：Run Launch / Preflight / Dispatch 编排。

事务边界：
- HTTP 请求线程只持久化 Run、NodeRun、ExecutionJob 与事件，不同步等待整条 Workflow；
- READY 前解析输入与能力预检；失败即 BLOCKED，不进入 QUEUED 后的 UNSUPPORTED_DRIVER；
- 一个 NodeRun 最多一个 ExecutionJob（DB 唯一约束 + 幂等 launch_key）。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services import dag_scheduler
from app.aiqe.services.preflight import preflight_graph, snapshot_manifests
from app.aiqe.services.event_service import append_event
from app.aiqe.services.execution_dispatcher import DispatchError, enqueue_node_run
from app.aiqe.services.execution_service import prepare_node
from app.aiqe.services.run_state import apply_transition
from app.aiqe.services.workflow_validator import (
    WorkflowValidationError,
    validate_workflow,
    workflow_checksum,
)
from app.core.config import settings
from app.models.environment import Environment


class LaunchError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class LaunchNotFound(LookupError):
    pass


def _event(
    db: Session,
    run: TestRun,
    event_type: str,
    payload: dict[str, Any],
    *,
    producer_event_id: str | None = None,
    node: NodeRun | None = None,
) -> None:
    append_event(
        db,
        run_id=run.id,
        event_type=event_type,
        payload={"schema_version": "1.0", **payload},
        producer="system",
        node_run_id=node.id if node else None,
        producer_event_id=producer_event_id,
    )


def _load_workflow(
    db: Session, workflow_id: str, project_id: int
) -> WorkflowDefinition:
    row = db.get(WorkflowDefinition, workflow_id)
    if row is None or int(row.project_id or 0) != int(project_id):
        raise LaunchNotFound(f"workflow 不存在: {workflow_id}")
    return row


def _assert_production_policy(db: Session, environment_id: int | None) -> None:
    env = db.get(Environment, environment_id) if environment_id else None
    is_prod = bool(env and getattr(env, "is_production", False))
    if settings.environment == "production":
        is_prod = True
    if is_prod and not settings.aiqe_prod_run_create_enabled:
        raise LaunchError(
            "PROD_RUN_CREATE_DISABLED",
            "生产环境 Run 创建默认关闭；请使用受控运维 smoke 或显式打开 "
            "AIQE_PROD_RUN_CREATE_ENABLED",
        )


def launch_run(
    db: Session,
    *,
    project_id: int,
    user_id: int | None,
    workflow_definition_id: str | None = None,
    graph_override: dict[str, Any] | None = None,
    expected_checksum: str | None = None,
    retest_of: str | None = None,
    environment_id: int | None = None,
    build_ref: str = "",
    commit_sha: str = "",
    run_key: str = "",
    launch_key: str = "",
    source_type: str = "manual",
    source_id: str = "",
    execution_profile_id: str | None = None,
    environment_snapshot: dict[str, Any] | None = None,
) -> TestRun:
    if graph_override is not None:
        graph = dict(graph_override)
        checksum = workflow_checksum(graph)
        if expected_checksum and checksum != expected_checksum:
            raise LaunchError(
                "WORKFLOW_CHECKSUM_MISMATCH",
                "冻结的 Workflow 快照 checksum 与 Run 记录不一致",
            )
        workflow_id = workflow_definition_id
        if workflow_id:
            # 只校验归属，避免回归使用跨项目 Workflow。
            _load_workflow(db, workflow_id, project_id)
    else:
        if not workflow_definition_id:
            raise LaunchError("WORKFLOW_REQUIRED", "缺少 workflow_definition_id")
        workflow = _load_workflow(db, workflow_definition_id, project_id)
        if workflow.approval_status != "approved":
            raise LaunchError("WORKFLOW_NOT_APPROVED", "Workflow 未审批，不能启动")
        graph = dict(workflow.graph_json or {})
        checksum = workflow_checksum(graph)
        if checksum != workflow.checksum:
            raise LaunchError(
                "WORKFLOW_CHECKSUM_MISMATCH",
                "Workflow 内容与审批时 checksum 不一致，拒绝执行",
            )
        workflow_id = workflow.id
    try:
        validate_workflow(
            graph,
            registered_drivers={
                "http",
                "playwright",
                "db",
                "event",
                "mobile",
                "miniapp",
                "device",
                "external_e2e",
                "appium",
            },
        )
    except WorkflowValidationError as exc:
        raise LaunchError("WORKFLOW_INVALID", str(exc)) from exc
    _assert_production_policy(db, environment_id)

    snapshot = dict(environment_snapshot or {})
    # secret 只允许 Runner 运行时注入；Run 快照只保留 key，不落明文。
    secret_values = snapshot.pop("secrets", None)
    if isinstance(secret_values, dict):
        snapshot.setdefault("secret_keys", sorted(str(key) for key in secret_values))
    if environment_id is not None:
        environment = db.get(Environment, environment_id)
        if environment is None or int(environment.project_id or 0) != int(project_id):
            raise LaunchError("ENVIRONMENT_NOT_FOUND", f"环境不存在: {environment_id}")
        snapshot.setdefault(
            "environment",
            {
                "id": environment.id,
                "name": environment.name,
                "base_url": environment.base_url,
                "is_production": bool(getattr(environment, "is_production", False)),
            },
        )
    if execution_profile_id:
        from app.aiqe.models.profile import ExecutionProfile

        profile = db.get(ExecutionProfile, execution_profile_id)
        if profile is None or int(profile.project_id or 0) != int(project_id):
            raise LaunchError("PROFILE_NOT_FOUND", f"Profile 不存在: {execution_profile_id}")
        if profile.approval_status != "approved":
            raise LaunchError(
                "PROFILE_NOT_APPROVED", f"Profile 未审批: {execution_profile_id}"
            )
        snapshot.setdefault(
            "execution_profile",
            {
                "id": profile.id,
                "name": profile.name,
                "purpose": profile.purpose,
                "version": profile.version,
                "checksum": profile.checksum,
            },
        )

    if launch_key:
        existing = db.scalar(
            select(TestRun).where(
                TestRun.project_id == project_id, TestRun.launch_key == launch_key
            )
        )
        if existing is not None:
            return existing

    report = preflight_graph(
        db,
        graph,
        project_id=project_id,
        environment_id=environment_id,
        profile_id=execution_profile_id,
        fixtures=snapshot.get("fixtures") or {},
    )
    run = TestRun(
        project_id=project_id,
        run_key=run_key or f"RUN-{uuid.uuid4().hex[:8]}",
        source_type=source_type,
        source_id=source_id or None,
        workflow_definition_id=workflow_id,
        workflow_checksum=checksum,
        workflow_snapshot_json=graph,
        retest_of=retest_of,
        launch_key=launch_key or None,
        environment_id=environment_id,
        execution_profile_id=execution_profile_id,
        build_ref=build_ref,
        commit_sha=commit_sha,
        environment_snapshot_json=snapshot,
        capability_snapshot_json=snapshot_manifests(db),
        preflight_json=report.model_dump(mode="json"),
        trigger_user_id=user_id,
        status="DRAFT",
    )
    db.add(run)
    db.flush()
    _event(db, run, "run.created", {"workflow_definition_id": workflow_id})

    nodes = dag_scheduler.create_node_runs(db, run.id, graph)
    if not report.ok:
        for issue in report.issues:
            for node in nodes:
                if node.node_key == issue.node_key:
                    node.status = "BLOCKED"
                    node.error_class = issue.code
        apply_transition(run, "BLOCKED")
        run.finished_at = None
        _event(
            db,
            run,
            "run.preflight_failed",
            {
                "issues": [issue.model_dump(mode="json") for issue in report.issues],
            },
            producer_event_id=f"run-preflight-failed:{run.id}",
        )
        db.flush()
        return run

    apply_transition(run, "VALIDATING")
    apply_transition(run, "QUEUED")
    _event(db, run, "run.queued", {"node_count": len(nodes)})

    def prepare(row: NodeRun) -> str | None:
        return prepare_node(db, run, row, graph)

    def dispatch(row: NodeRun) -> None:
        try:
            job = enqueue_node_run(db, row, graph=graph)
        except DispatchError:
            raise
        _event(
            db,
            run,
            "job.dispatched",
            {
                "job_id": job.id,
                "node_key": row.node_key,
                "driver": row.driver_key,
                "attempt": job.attempt,
            },
            producer_event_id=f"job-dispatched:{row.id}:{job.id}",
            node=row,
        )

    try:
        dag_scheduler.schedule(db, run.id, graph, dispatch=dispatch, prepare=prepare)
    except Exception:
        # 调度异常必须把 Run 置 ERROR，不能停在 QUEUED/RUNNING 悬挂。
        if run.status in {"QUEUED", "RUNNING"}:
            apply_transition(run, "ERROR")
        db.flush()
        raise
    if run.status == "QUEUED":
        apply_transition(run, "RUNNING")
    db.flush()
    return run


def cancel_run(
    db: Session, *, project_id: int, run_id: str, user_id: int | None = None
) -> TestRun:
    run = db.get(TestRun, run_id)
    if run is None or int(run.project_id or 0) != int(project_id):
        raise LaunchNotFound(run_id)
    if run.status in {"COMPLETED", "BLOCKED", "CANCELED", "ERROR"}:
        raise LaunchError("RUN_TERMINAL", f"Run 已是终态: {run.status}")
    from app.models.execution_job import ExecutionJob

    nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    for node in nodes:
        if node.execution_job_id:
            job = db.get(ExecutionJob, node.execution_job_id)
            if job is not None and job.status in {"pending", "running"}:
                job.status = "canceled"
                job.finished_at = datetime.now(UTC)
        if node.status not in {"PASSED", "FAILED", "BLOCKED", "SKIPPED", "CANCELED", "ERROR"}:
            node.status = "CANCELED"
            node.error_class = "RUN_CANCELED"
    apply_transition(run, "CANCELED")
    run.finished_at = datetime.now(UTC)
    _event(
        db,
        run,
        "run.canceled",
        {"by_user_id": user_id},
        producer_event_id=f"run-canceled:{run.id}",
    )
    db.flush()
    return run
