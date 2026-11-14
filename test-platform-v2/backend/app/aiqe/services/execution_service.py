"""AIQE 执行服务（v1.4 FIX-001/002/003/004/006/008 的服务层编排）。

流程（in-process 与外部 Runner 共用同一收口逻辑）：
1. READY 前解析输入（RunContext）→ 失败则 BLOCKED，不派发；
2. 节点执行（NodeExecutor / 外部上报）→ DriverResult；
3. Assertion Runtime 执行机器断言并落 `run_assertion_results`；
4. 按节点声明的 outputs 提取结构化输出（失败 = OUTPUT_SCHEMA_MISMATCH）；
5. 证据脱敏后写 Artifact；大文件只存 URI/sha256；
6. 通过唯一状态机收口 NodeRun/TestRun，并写 RunEvent。

任何一步都不能把 NOT_EVALUATED / BLOCKED 折算成 PASS。
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.schemas.contracts import DriverResult, EvidenceFile
from app.aiqe.services import assertion_service, dag_scheduler, evidence_redactor
from app.aiqe.services.artifact_service import put_artifact
from app.aiqe.services.event_service import append_event
from app.aiqe.services.node_executor import NodeExecution, execute_node
from app.aiqe.services.run_context import (
    EnvSecretProvider,
    RunContext,
    VariableResolutionError,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

TEXT_ARTIFACT_TYPES = frozenset({"request", "response", "log", "dom", "a11y", "report", "db_snapshot"})


def _now() -> datetime:
    return datetime.now(UTC)


def _event(
    db: Session,
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    node: NodeRun | None = None,
    attempt: StepAttempt | None = None,
    producer: str = "node",
    producer_event_id: str | None = None,
) -> None:
    safe_payload = {"schema_version": "1.0", **payload}
    append_event(
        db,
        run_id=run_id,
        event_type=event_type,
        payload=safe_payload,
        producer=producer,  # type: ignore[arg-type]
        node_run_id=node.id if node else None,
        step_attempt_id=attempt.id if attempt else None,
        producer_event_id=producer_event_id,
    )


def _latest_attempt(db: Session, node: NodeRun) -> StepAttempt | None:
    return db.scalar(
        select(StepAttempt)
        .where(StepAttempt.node_run_id == node.id)
        .order_by(StepAttempt.attempt_no.desc())
    )


def _graph_node(graph: Mapping[str, Any], node_key: str) -> dict[str, Any]:
    for node in graph.get("nodes") or []:
        if isinstance(node, Mapping) and str(node.get("key")) == node_key:
            return dict(node)
    return {}


def _secret_provider(run: TestRun, explicit: Any = None):
    if explicit is not None:
        return explicit
    snapshot = run.environment_snapshot_json or {}
    secrets = snapshot.get("secrets") if isinstance(snapshot, Mapping) else None
    if isinstance(secrets, Mapping):
        from app.aiqe.services.run_context import MappingSecretProvider

        return MappingSecretProvider(secrets)
    return EnvSecretProvider()


def prepare_node(
    db: Session,
    run: TestRun,
    node: NodeRun,
    graph: Mapping[str, Any],
    *,
    secret_provider: Any = None,
) -> str | None:
    """解析节点输入并持久化脱敏快照；返回错误码（None 表示成功）。"""
    ctx = RunContext(
        db,
        run.id,
        graph=graph,
        secrets=_secret_provider(run, secret_provider),
        fixtures=(run.environment_snapshot_json or {}).get("fixtures") or {},
    )
    try:
        resolved = ctx.resolve_node_input(node.node_key, node.input_ref or {})
    except VariableResolutionError as exc:
        node.status = "BLOCKED"
        node.error_class = exc.code
        _event(
            db,
            run.id,
            "node.blocked",
            {"reason": str(exc), "code": exc.code},
            node=node,
            producer_event_id=f"node-blocked:{node.id}:{exc.code}",
        )
        return exc.code
    ctx.persist_resolved_input(node, resolved)
    _event(
        db,
        run.id,
        "node.input_resolved",
        {
            "source_refs": [ref.model_dump(mode="json") for ref in resolved.source_refs],
            "secret_keys": resolved.secret_keys,
        },
        node=node,
        producer_event_id=f"node-input-resolved:{node.id}",
    )
    return None


def _legacy_assertions(node: NodeRun) -> list[dict[str, Any]]:
    """兼容 PR #595 前的 workflow：`expected_status` 等价于一条 http_status 断言。"""
    if node.assertions_json:
        return list(node.assertions_json)
    raw = node.input_ref or {}
    assertions: list[dict[str, Any]] = []
    expected_status = raw.get("expected_status")
    if expected_status is not None:
        try:
            expected = int(expected_status)
        except (TypeError, ValueError):
            expected = None
        if expected is not None:
            assertions.append(
                {
                    "assertion_key": "http_status",
                    "oracle_layer": "STD",
                    "oracle_ref": f"workflow:{node.node_key}:expected_status",
                    "type": "http_status",
                    "operator": "eq",
                    "expected": expected,
                    "severity": "P0",
                }
            )
    expect_text = raw.get("expect_text")
    if expect_text:
        assertions.append(
            {
                "assertion_key": "expect_text",
                "oracle_layer": "STD",
                "oracle_ref": f"workflow:{node.node_key}:expect_text",
                "type": "text_contains",
                "operator": "contains",
                "expected": str(expect_text),
                "severity": "P1",
            }
        )
    return assertions


def _map_driver_status(status: str) -> str:
    return {
        "PASSED": "SUCCEEDED",
        "SUCCEEDED": "SUCCEEDED",
        "FAILED": "FAILED",
        "BLOCKED": "BLOCKED",
        "ERROR": "ERROR",
    }.get(str(status).upper(), "ERROR")


def _execution_to_result(node: NodeRun, execution: NodeExecution) -> DriverResult:
    return DriverResult(
        driver_key=node.driver_key or "",
        status=_map_driver_status(execution.status),  # type: ignore[arg-type]
        data=dict(execution.data or {}),
        error_class=execution.error_class,
        error_message=str(execution.detail.get("reason") or execution.error_class or "")[:500],
        duration_ms=int(execution.detail.get("duration_ms") or 0),
        evidence=list(execution.evidence),
    )


def _upload_text_artifact(
    db: Session,
    *,
    run: TestRun,
    node: NodeRun,
    attempt: StepAttempt,
    kind: str,
    payload: Any,
    known_secrets: Iterable[str],
    mime: str = "application/json",
    extra_fields: Iterable[str] = (),
) -> str | None:
    cleaned = evidence_redactor.redact(
        payload,
        extra_sensitive_fields=extra_fields,
        known_secrets=known_secrets,
    )
    content = json.dumps(cleaned, ensure_ascii=False, default=str).encode("utf-8")
    row = put_artifact(
        db,
        project_id=run.project_id,
        run_id=run.id,
        content=content,
        artifact_type=kind,
        mime_type=mime,
        node_run_id=node.id,
        step_attempt_id=attempt.id,
        metadata={"redacted": True, "source": "execution_service"},
        redaction_status="sanitized",
    )
    return row.id


def _upload_binary_artifact(
    db: Session,
    *,
    run: TestRun,
    node: NodeRun,
    attempt: StepAttempt,
    file: EvidenceFile,
    known_secrets: Iterable[str],
    extra_fields: Iterable[str] = (),
) -> str | None:
    if file.artifact_type in TEXT_ARTIFACT_TYPES:
        try:
            text = file.content.decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(text)
            except (TypeError, ValueError):
                parsed = text
            return _upload_text_artifact(
                db,
                run=run,
                node=node,
                attempt=attempt,
                kind=file.artifact_type,
                payload=parsed,
                known_secrets=known_secrets,
                mime=file.mime_type,
                extra_fields=extra_fields,
            )
        except Exception:
            pass
    hits = evidence_redactor.scan_bytes(file.content, known_secrets=known_secrets)
    if hits:
        _event(
            db,
            run.id,
            "artifact.rejected",
            {"artifact_type": file.artifact_type, "reason": "secret_scan_hit", "hits": hits},
            node=node,
            attempt=attempt,
            producer_event_id=f"artifact-rejected:{attempt.id}:{file.name}",
        )
        return None
    row = put_artifact(
        db,
        project_id=run.project_id,
        run_id=run.id,
        content=file.content,
        artifact_type=file.artifact_type,
        mime_type=file.mime_type,
        node_run_id=node.id,
        step_attempt_id=attempt.id,
        metadata={"redacted": True, "source": "driver", "name": file.name, **(file.metadata or {})},
        redaction_status="sanitized",
    )
    return row.id


def persist_execution_evidence(
    db: Session,
    *,
    run: TestRun,
    node: NodeRun,
    attempt: StepAttempt,
    execution: NodeExecution,
    known_secrets: Iterable[str] = (),
) -> list[str]:
    artifact_ids: list[str] = []
    detail = execution.detail or {}
    if detail.get("request"):
        artifact_id = _upload_text_artifact(
            db,
            run=run,
            node=node,
            attempt=attempt,
            kind="request",
            payload=detail["request"],
            known_secrets=known_secrets,
        )
        if artifact_id:
            artifact_ids.append(artifact_id)
    if detail.get("response"):
        artifact_id = _upload_text_artifact(
            db,
            run=run,
            node=node,
            attempt=attempt,
            kind="response",
            payload=detail["response"],
            known_secrets=known_secrets,
        )
        if artifact_id:
            artifact_ids.append(artifact_id)
    if execution.data.get("db"):
        artifact_id = _upload_text_artifact(
            db,
            run=run,
            node=node,
            attempt=attempt,
            kind="db_snapshot",
            payload=execution.data["db"],
            known_secrets=known_secrets,
        )
        if artifact_id:
            artifact_ids.append(artifact_id)
    for file in execution.evidence:
        artifact_id = _upload_binary_artifact(
            db,
            run=run,
            node=node,
            attempt=attempt,
            file=file,
            known_secrets=known_secrets,
        )
        if artifact_id:
            artifact_ids.append(artifact_id)
    return artifact_ids


def finalize_node(
    db: Session,
    *,
    run: TestRun,
    node: NodeRun,
    graph: Mapping[str, Any],
    execution: NodeExecution,
    attempt: StepAttempt | None,
    known_secrets: Iterable[str] = (),
    artifact_ids: list[str] | None = None,
) -> dict[str, Any]:
    """断言 → outputs → evidence → 状态收口（in-process / external 共用）。"""
    if attempt is None:
        attempt = _latest_attempt(db, node)
    if attempt is None:
        attempt = StepAttempt(
            node_run_id=node.id,
            step_key=node.node_key,
            attempt_no=max(1, int(node.attempt_count or 1)),
            status="RUNNING",
            started_at=_now(),
        )
        db.add(attempt)
        db.flush()
    result = _execution_to_result(node, execution)
    declarations = _legacy_assertions(node)
    assertion_status: str = assertion_service.NOT_EVALUATED
    outcomes: list[assertion_service.AssertionOutcome] = []
    try:
        assertion_status, outcomes = assertion_service.evaluate_and_persist(
            db,
            node=node,
            attempt=attempt,
            result=result,
            declared=declarations,
            known_secrets=known_secrets,
        )
    except assertion_service.AssertionConfigError as exc:
        # 配置错误是 ERROR，不是业务 FAIL；断言结果落一条 ERROR 记录。
        logger.warning("assertion config error on %s: %s", node.node_key, exc)
        assertion_status = assertion_service.ERROR
        outcomes = []
        assertion_service.persist_outcomes(
            db,
            attempt,
            [
                assertion_service.AssertionOutcome(
                    assertion_key="assertion_config",
                    type="config",
                    oracle_layer="STD",
                    oracle_ref="assertion:config",
                    status=assertion_service.ERROR,
                    actual=None,
                    error=str(exc)[:500],
                )
            ],
            known_secrets=known_secrets,
        )
    if artifact_ids:
        for row in attempt.assertion_results:
            if row.artifact_refs_json:
                continue
            row.artifact_refs_json = list(artifact_ids)
            row.evidence_refs_json = list(artifact_ids)
        db.flush()

    outputs: dict[str, Any] = {}
    output_error = ""
    outputs_spec = dict(node.outputs_spec_json or {})
    if outputs_spec:
        ctx = RunContext(db, run.id, graph=graph)
        try:
            outputs = ctx.capture_node_outputs(
                node, result, outputs_spec, node.output_schema_json
            )
        except VariableResolutionError as exc:
            output_error = exc.code
            node.error_class = exc.code
            _event(
                db,
                run.id,
                "node.output_mismatch",
                {"code": exc.code, "reason": str(exc)},
                node=node,
                attempt=attempt,
                producer_event_id=f"node-output-mismatch:{attempt.id}",
            )
    elif node.output_schema_json:
        # 没有 outputs 映射但声明了 schema 时，以 data 作为输出整体校验。
        ctx = RunContext(db, run.id, graph=graph)
        try:
            ctx.capture_node_outputs(
                node, result, {"data": "$.data"}, node.output_schema_json
            )
            outputs = {"data": result.data.get("data")}
        except VariableResolutionError as exc:
            output_error = exc.code
            node.error_class = exc.code

    driver_status = execution.status.upper()
    if output_error:
        node_status = "BLOCKED"
    elif driver_status in {"BLOCKED", "ERROR", "FAILED"}:
        node_status = driver_status
    elif assertion_status == assertion_service.PASS:
        node_status = "PASSED"
    elif assertion_status == assertion_service.FAIL:
        node_status = "FAILED"
    elif assertion_status == assertion_service.ERROR:
        node_status = "ERROR"
    elif not declarations:
        # 非业务节点（setup/cleanup）允许在 driver 成功后通过；事件会标明没有断言。
        node_status = "PASSED"
    else:
        node_status = "BLOCKED"

    # 断言失败要给可分类错误码（driver 成功但业务断言失败时不能留空）。
    if not node.error_class:
        if execution.error_class and driver_status in {"BLOCKED", "ERROR", "FAILED"}:
            node.error_class = execution.error_class
        elif node_status == "FAILED" and declarations:
            has_http_status = any(
                str(item.get("type")) == "http_status" for item in declarations
            )
            node.error_class = "STATUS_MISMATCH" if has_http_status else "ASSERTION_FAILED"
        elif node_status == "BLOCKED" and declarations:
            node.error_class = "ASSERTION_BLOCKED"
        elif node_status == "ERROR" and declarations:
            node.error_class = "ASSERTION_ERROR"

    dag_scheduler.complete_node(
        db,
        run.id,
        node.node_key,
        node_status,
        dict(graph),
        error_class=(node.error_class or execution.error_class or None),
        outputs=outputs,
    )
    _event(
        db,
        run.id,
        "node.completed",
        {
            "status": node_status,
            "driver_status": execution.status,
            "assertion_status": assertion_status,
            "assertion_count": len(outcomes),
            "output_keys": sorted(outputs),
            "error_class": node.error_class or execution.error_class,
            "artifact_ids": list(artifact_ids or []),
        },
        node=node,
        attempt=attempt,
        producer_event_id=f"node-completed:{attempt.id}",
    )
    attempt.status = node_status
    attempt.finished_at = attempt.finished_at or _now()
    attempt.output_summary_json = dict(outputs or {})
    db.flush()
    return {
        "node_key": node.node_key,
        "node_status": node_status,
        "status": node_status,
        "error_class": node.error_class or execution.error_class,
        "assertion_status": assertion_status,
        "assertions": [
            {
                "assertion_key": item.assertion_key,
                "status": item.status,
                "actual": item.actual,
                "expected": item.expected,
                "error": item.error,
            }
            for item in outcomes
        ],
        "outputs": outputs,
        "artifacts": list(artifact_ids or []),
    }


def _advance_run(db: Session, run: TestRun, graph: Mapping[str, Any]) -> None:
    """节点完成后推进 DAG：解析下游输入并派发新 Job。"""
    if run.status != "RUNNING":
        return
    from app.aiqe.services.execution_dispatcher import enqueue_node_run

    def prepare(row: NodeRun) -> str | None:
        return prepare_node(db, run, row, graph)

    def dispatch(row: NodeRun) -> None:
        job = enqueue_node_run(db, row, graph=dict(graph))
        _event(
            db,
            run.id,
            "job.dispatched",
            {
                "job_id": job.id,
                "node_key": row.node_key,
                "driver": row.driver_key,
                "attempt": job.attempt,
            },
            node=row,
            producer_event_id=f"job-dispatched:{row.id}:{job.id}",
        )

    try:
        dag_scheduler.schedule(db, run.id, dict(graph), dispatch=dispatch, prepare=prepare)
    except Exception:
        logger.exception("advance run %s failed", run.id)
        if run.status == "RUNNING":
            from app.aiqe.services.run_state import apply_transition

            apply_transition(run, "ERROR")
        raise


def execute_inprocess_job(db: Session, job_id: int) -> dict[str, Any]:
    """进程内执行一个 AIQE ExecutionJob（HTTP 节点）。"""
    from app.models.execution_job import ExecutionJob

    job = db.get(ExecutionJob, job_id)
    if job is None or job.status != "running":
        return {"job_id": job_id, "skipped": True}
    payload = json.loads(job.payload_json or "{}")
    run = db.get(TestRun, str(payload.get("run_id") or ""))
    node = db.get(NodeRun, str(payload.get("node_run_id") or ""))
    if run is None or node is None:
        job.status = "failed"
        job.error_message = "run/node not found"
        job.finished_at = _now()
        db.commit()
        return {"job_id": job_id, "status": "failed", "reason": "missing run/node"}
    graph = dict(payload.get("graph") or {"nodes": [{"key": node.node_key}], "edges": []})
    if node.status == "READY":
        dag_scheduler.mark_running(db, run.id, node.node_key)
    attempt = _latest_attempt(db, node)
    _event(
        db,
        run.id,
        "node.started",
        {"driver": node.driver_key},
        node=node,
        attempt=attempt,
        producer_event_id=f"node-started:{attempt.id if attempt else node.id}",
    )

    # 解析输入（含 secret；secret 只在内存中）。
    ctx = RunContext(
        db,
        run.id,
        graph=graph,
        secrets=_secret_provider(run),
        fixtures=(run.environment_snapshot_json or {}).get("fixtures") or {},
    )
    try:
        resolved = ctx.resolve_node_input(node.node_key, node.input_ref or {})
    except VariableResolutionError as exc:
        node.status = "BLOCKED"
        node.error_class = exc.code
        _event(
            db,
            run.id,
            "node.blocked",
            {"code": exc.code, "reason": str(exc)},
            node=node,
            attempt=attempt,
            producer_event_id=f"node-blocked:{node.id}:{exc.code}",
        )
        job.status = "failed"
        job.error_message = exc.code
        job.finished_at = _now()
        db.commit()
        return {"job_id": job_id, "run_id": run.id, "node": node.node_key, "status": "BLOCKED", "error_class": exc.code}

    execution = execute_node(
        node,
        input_override=dict(resolved.values),
        db_engine=readonly_db_engine(),
    )
    known_secrets = list(ctx.last_secret_values)
    artifact_ids = persist_execution_evidence(
        db,
        run=run,
        node=node,
        attempt=attempt,  # type: ignore[arg-type]
        execution=execution,
        known_secrets=known_secrets,
    ) if attempt is not None else []
    summary = finalize_node(
        db,
        run=run,
        node=node,
        graph=graph,
        execution=execution,
        attempt=attempt,
        known_secrets=known_secrets,
        artifact_ids=artifact_ids,
    )
    job.status = "success" if summary["status"] == "PASSED" else "failed"
    job.result_json = json.dumps(
        {"detail": execution.detail, "data": execution.data, "summary": summary},
        ensure_ascii=False,
        default=str,
    )[:20000]
    job.summary = f"{node.node_key}:{summary['status']}"
    job.error_message = node.error_class or execution.error_class
    job.finished_at = _now()
    _advance_run(db, run, graph)
    db.commit()
    return {"job_id": job_id, "run_id": run.id, **summary}


def complete_from_external_report(
    db: Session,
    *,
    job_id: int,
    status: str,
    result: Mapping[str, Any] | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    """外部 Runner 上报后走同一断言/证据/状态收口。"""
    from app.models.execution_job import ExecutionJob

    job = db.get(ExecutionJob, job_id)
    if job is None:
        return {"skipped": True, "reason": "job missing"}
    payload = json.loads(job.payload_json or "{}")
    run = db.get(TestRun, str(payload.get("run_id") or ""))
    node = db.get(NodeRun, str(payload.get("node_run_id") or ""))
    if run is None or node is None:
        return {"skipped": True, "reason": "node/run missing"}
    graph = dict(payload.get("graph") or {"nodes": [{"key": node.node_key}], "edges": []})
    if node.status == "READY":
        dag_scheduler.mark_running(db, run.id, node.node_key)
    attempt = _latest_attempt(db, node)
    reported = dict(result or {})
    passed = str(reported.get("status") or status).lower() in {
        "completed",
        "success",
        "passed",
        "pass",
        "ok",
        "succeeded",
    }
    data = reported.get("data") if isinstance(reported.get("data"), Mapping) else {}
    if not data:
        data = {
            key: value
            for key, value in reported.items()
            if key
            not in {
                "status",
                "error_class",
                "error_message",
                "driver_result",
                "evidence",
            }
        }
    driver_status = str(reported.get("driver_status") or "").upper()
    if driver_status not in {"SUCCEEDED", "FAILED", "BLOCKED", "ERROR"}:
        driver_status = "SUCCEEDED" if passed else "FAILED"
    error_class = str(reported.get("error_class") or (error_message or "")).strip()[:80]
    execution = NodeExecution(
        status={
            "SUCCEEDED": "PASSED",
            "FAILED": "FAILED",
            "BLOCKED": "BLOCKED",
            "ERROR": "ERROR",
        }[driver_status],
        error_class=error_class,
        detail=dict(reported),
        data=dict(data),
        evidence=[],
    )
    known_secrets: list[str] = []
    artifact_ids = persist_execution_evidence(
        db,
        run=run,
        node=node,
        attempt=attempt,  # type: ignore[arg-type]
        execution=execution,
        known_secrets=known_secrets,
    ) if attempt is not None else []
    summary = finalize_node(
        db,
        run=run,
        node=node,
        graph=graph,
        execution=execution,
        attempt=attempt,
        known_secrets=known_secrets,
        artifact_ids=artifact_ids,
    )
    _event(
        db,
        run.id,
        "node.reported",
        {
            "reported_status": status,
            "driver_status": driver_status,
            "error_class": error_class,
            "status": summary["status"],
        },
        node=node,
        attempt=attempt,
        producer_event_id=f"node-reported:{job_id}:{status}",
    )
    _advance_run(db, run, graph)
    db.commit()
    return {"job_id": job_id, "run_id": run.id, **summary}


# ── 只读 DB engine（供 DB-RO Driver 使用）──────────────────────────────
_DB_ENGINE = None


def readonly_db_engine():
    global _DB_ENGINE
    if _DB_ENGINE is not None:
        return _DB_ENGINE
    url = str(settings.aiqe_db_readonly_url or "").strip()
    if not url:
        return None
    _DB_ENGINE = create_engine(url, pool_pre_ping=True)
    return _DB_ENGINE


def resolve_node_input_for_dispatch(
    db: Session,
    run: TestRun,
    node: NodeRun,
    graph: Mapping[str, Any],
) -> str | None:
    """调度前解析输入；失败返回错误码。"""
    return prepare_node(db, run, node, graph)
