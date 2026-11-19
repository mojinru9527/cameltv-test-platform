"""v1.4 FIX-006：Run Launch / Preflight / Dispatch 编排。

事务边界：
- HTTP 请求线程只持久化 Run、NodeRun、ExecutionJob 与事件，不同步等待整条 Workflow；
- READY 前解析输入与能力预检；失败即 BLOCKED，不进入 QUEUED 后的 UNSUPPORTED_DRIVER；
- 一个 NodeRun 最多一个 ExecutionJob（DB 唯一约束 + 幂等 launch_key）。
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services import dag_scheduler
from app.aiqe.services.preflight import preflight_graph, snapshot_manifests
from app.aiqe.services.snapshot_service import (
    ensure_snapshot,
    get_snapshot,
    snapshot_from_graph,
    snapshot_graph,
)
from app.aiqe.services.event_service import append_event
from app.aiqe.services.execution_dispatcher import DispatchError, enqueue_node_run
from app.aiqe.services import outbox_service
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
    workflow_snapshot_id: str | None = None,
    execution_kind: str = "NORMAL",
    scope_snapshot: Mapping[str, Any] | None = None,
) -> TestRun:
    freeze = None
    if workflow_snapshot_id:
        freeze = get_snapshot(db, workflow_snapshot_id, project_id=project_id)
        graph = snapshot_graph(freeze)
        checksum = freeze.checksum_sha256
        workflow_id = freeze.workflow_id
        if expected_checksum and checksum != expected_checksum:
            raise LaunchError(
                "WORKFLOW_CHECKSUM_MISMATCH",
                "冻结的 Workflow 快照 checksum 与请求不一致",
            )
        validate_workflow(
            graph, registered_drivers={"http", "playwright", "db", "event", "mobile", "miniapp", "device", "external_e2e", "appium"}
        )
    elif graph_override is not None:
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
        freeze = snapshot_from_graph(
            db,
            project_id=project_id,
            graph=graph,
            workflow_id=workflow_id,
            execution_kind=execution_kind,
            created_by=user_id,
        )
    else:
        if not workflow_definition_id:
            raise LaunchError("WORKFLOW_REQUIRED", "缺少 workflow_definition_id")
        workflow = _load_workflow(db, workflow_definition_id, project_id)
        if workflow.approval_status != "approved":
            raise LaunchError("WORKFLOW_NOT_APPROVED", "Workflow 未审批，不能启动")
        # V16-001 §5：旧字段无法迁移为服务端策略的 Workflow 暂停执行，必须人工复核。
        if str(getattr(workflow, "policy_status", "") or "").upper() == "NEEDS_POLICY_REVIEW":
            raise LaunchError(
                "WORKFLOW_NEEDS_POLICY_REVIEW",
                "Workflow 的旧目标字段无法自动迁移为服务端策略，需管理员配置 TargetPolicy 后重新审批",
            )
        graph = dict(workflow.graph_json or {})
        checksum = workflow_checksum(graph)
        if checksum != workflow.checksum:
            raise LaunchError(
                "WORKFLOW_CHECKSUM_MISMATCH",
                "Workflow 内容与审批时 checksum 不一致，拒绝执行",
            )
        workflow_id = workflow.id
        freeze = ensure_snapshot(
            db, workflow, execution_kind=execution_kind, created_by=user_id
        )
        graph = snapshot_graph(freeze)
        checksum = freeze.checksum_sha256
    if freeze is None:
        raise LaunchError("WORKFLOW_REQUIRED", "缺少可冻结的 Workflow 快照")
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

    # V16-008：回归必须携带服务端 Scope Snapshot；mandatory 节点不得被排除。
    if scope_snapshot is not None:
        scope_payload = dict(scope_snapshot)
        graph_keys = {str(node.get("key")) for node in graph.get("nodes") or []}
        mandatory_keys = [str(key) for key in scope_payload.get("mandatory_node_keys") or []]
        missing = [key for key in mandatory_keys if key not in graph_keys]
        if missing:
            raise LaunchError(
                "MANDATORY_SCOPE_VIOLATION",
                f"mandatory 节点不在执行 DAG 中: {sorted(missing)}",
            )
        snapshot["scope_snapshot"] = scope_payload
        if scope_payload.get("scope_id"):
            snapshot["scope_snapshot_id"] = str(scope_payload["scope_id"])
    elif str(execution_kind) == "DEFECT_REGRESSION":
        raise LaunchError(
            "SCOPE_SNAPSHOT_REQUIRED", "Defect Regression 必须携带服务端 Scope Snapshot"
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
        workflow_snapshot_id=freeze.id,
        execution_kind=str(execution_kind),
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
    _event(
        db,
        run,
        "run.created",
        {
            "workflow_definition_id": workflow_id,
            "workflow_snapshot_id": freeze.id,
            "workflow_snapshot_hash": checksum,
            "execution_kind": str(execution_kind),
        },
    )

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
        outbox_service.enqueue(
            db,
            project_id=run.project_id,
            run_id=run.id,
            event_type="run.preflight_failed",
            payload={
                "run_id": run.id,
                "snapshot_id": freeze.id,
                "blocked_reason": str(report.issues[0].code if report.issues else "PREFLIGHT_BLOCKED"),
            },
            producer_event_id=f"run-preflight-failed-outbox:{run.id}",
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
    # V16-006 §6：Launch 返回 QUEUED；只有 Worker 真正 claim 后才进入 RUNNING
    # （dag_scheduler.mark_running 在认领/执行时迁移），API 不得提前宣称 RUNNING。
    # V16-006：Run/NodeRun/Job 与 Outbox 事件同事务写入；relay 幂等发布。
    dispatched_job_ids = [
        int(job_id)
        for job_id in db.scalars(
            select(NodeRun.execution_job_id).where(
                NodeRun.run_id == run.id, NodeRun.execution_job_id.is_not(None)
            )
        )
        if job_id is not None
    ]
    outbox_service.enqueue(
        db,
        project_id=run.project_id,
        run_id=run.id,
        event_type="run.dispatched",
        payload={
            "run_id": run.id,
            "snapshot_id": freeze.id,
            "snapshot_hash": checksum,
            "execution_kind": str(execution_kind),
            "job_ids": sorted(dispatched_job_ids),
        },
        producer_event_id=f"run-dispatched:{run.id}",
    )
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
    outbox_service.enqueue(
        db,
        project_id=run.project_id,
        run_id=run.id,
        event_type="run.canceled",
        payload={"run_id": run.id, "by_user_id": user_id},
        producer_event_id=f"run-canceled-outbox:{run.id}",
    )
    _event(
        db,
        run,
        "run.canceled",
        {"by_user_id": user_id},
        producer_event_id=f"run-canceled:{run.id}",
    )
    db.flush()
    return run

@dataclass(frozen=True)
class LaunchResult:
    """V16-006：统一 Launch 契约（唯一正式执行入口的返回值）。"""

    run_id: str
    run_status: str
    job_ids: tuple[int, ...] = ()
    node_run_ids: tuple[str, ...] = ()
    snapshot_id: str = ""
    snapshot_hash: str = ""
    execution_kind: str = "NORMAL"
    dispatch_status: str = ""
    blocked_reason: str = ""
    outbox_pending: int = 0


def build_launch_result(db: Session, run: TestRun) -> LaunchResult:
    """从持久化事实计算 LaunchResult（不依赖调用方传参）。"""
    from app.models.execution_job import ExecutionJob

    job_ids = tuple(
        int(job_id)
        for job_id in db.scalars(
            select(ExecutionJob.id)
            .where(ExecutionJob.run_id == run.id)
            .order_by(ExecutionJob.id)
        )
    )
    node_ids = tuple(
        str(node_id)
        for node_id in db.scalars(
            select(NodeRun.id).where(NodeRun.run_id == run.id).order_by(NodeRun.id)
        )
    )
    blocked_reason = ""
    if str(run.status) == "BLOCKED":
        issues = list((run.preflight_json or {}).get("issues") or [])
        blocked_reason = str(issues[0].get("code") or "PREFLIGHT_BLOCKED") if issues else "BLOCKED"
    dispatch_status = {
        "BLOCKED": "BLOCKED",
        "QUEUED": "DISPATCHED",
        "RUNNING": "DISPATCHED",
    }.get(str(run.status), "")
    return LaunchResult(
        run_id=run.id,
        run_status=str(run.status),
        job_ids=job_ids,
        node_run_ids=node_ids,
        snapshot_id=str(run.workflow_snapshot_id or ""),
        snapshot_hash=str(run.workflow_checksum or ""),
        execution_kind=str(run.execution_kind or "NORMAL"),
        dispatch_status=dispatch_status,
        blocked_reason=blocked_reason,
        outbox_pending=outbox_service.pending_count(db),
    )


def launch(db: Session, *, project_id: int, user_id: int | None = None, **kwargs: Any) -> LaunchResult:
    """V16-006 正式入口：与 launch_run 共用同一实现，返回结构化 LaunchResult。

    所有 Run 类型（NORMAL/NOISE_EXPERIMENT/DEFECT_REGRESSION）都必须走这里。
    """
    run = launch_run(db, project_id=project_id, user_id=user_id, **kwargs)
    return build_launch_result(db, run)
