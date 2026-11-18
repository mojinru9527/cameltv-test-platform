"""M1 / TA-008：Run Console 只读 API + SSE 事件流。

- 全部按 `X-Project-Id` 隔离，并统一要求执行中心权限 `menu:aiqe_runs`（batch-336）；
- 事件流支持 `after_seq` 断线补拉；`once=1` 时只推一批（测试/调试用）；
- 路由层禁止 ORM：查询全部走 `run_query_service`。
"""
from __future__ import annotations

import json
import time
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.aiqe.services.event_service import list_events
from app.aiqe.services.run_launch import LaunchError, LaunchNotFound, cancel_run, launch_run
from app.aiqe.services.run_state import TERMINAL_STATUSES
from app.aiqe.services.run_query_service import (
    RunNotFoundError,
    get_artifacts,
    get_events,
    get_run,
    get_run_assertions,
    get_run_attempts,
    get_run_detail,
    get_run_nodes,
    list_runs,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.aiqe_run import RunArtifactOut, RunEventOut, RunLaunchIn, RunOut
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/runs", tags=["aiqe-runs"])


def _not_found(run_id: str) -> APIException:
    return APIException(code=404, msg=f"Run 不存在: {run_id}", http_status=404)


def _run_dict(run) -> dict:
    return RunOut.model_validate(run).model_dump(mode="json")


def _launch_error(exc: Exception) -> APIException:
    if isinstance(exc, LaunchNotFound):
        return APIException(code=404, msg=str(exc), http_status=404)
    code = getattr(exc, "code", "RUN_LAUNCH_FAILED")
    status = 403 if code == "PROD_RUN_CREATE_DISABLED" else 409
    if code == "WORKFLOW_NOT_APPROVED":
        status = 409
    return APIException(code=status, msg=f"{code}: {exc}", http_status=status)


@router.post("", response_model=R[dict], summary="创建并启动 Run（Preflight + DAG 派发）")
def create_run_api(
    body: RunLaunchIn,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        run = launch_run(
            db,
            project_id=current.project_id or 0,
            user_id=current.user.id,
            workflow_definition_id=body.workflow_definition_id,
            environment_id=body.environment_id,
            build_ref=body.build_ref,
            commit_sha=body.commit_sha,
            run_key=body.run_key,
            launch_key=body.launch_key,
            source_type=body.source_type,
            source_id=body.source_id,
            execution_profile_id=body.execution_profile_id,
            environment_snapshot=body.environment_snapshot,
        )
        db.commit()
    except (LaunchError, LaunchNotFound) as exc:
        db.rollback()
        raise _launch_error(exc) from None
    return R.ok(
        {
            "run": _run_dict(run),
            "preflight": run.preflight_json or {},
            "node_count": len(run.node_runs or []),
        }
    )


@router.post("/{run_id}/cancel", response_model=R[dict], summary="取消 Run")
def cancel_run_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        run = cancel_run(
            db, project_id=current.project_id or 0, run_id=run_id, user_id=current.user.id
        )
        db.commit()
    except LaunchNotFound:
        db.rollback()
        raise _not_found(run_id) from None
    except LaunchError as exc:
        db.rollback()
        raise APIException(code=409, msg=str(exc), http_status=409) from None
    return R.ok({"run": _run_dict(run)})


@router.get("", response_model=R[dict], summary="Run 列表")
def list_runs_api(
    status: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    rows, total = list_runs(
        db, project_id=current.project_id or 0, status=status, limit=limit, offset=offset
    )
    return R.ok(
        {
            "items": [RunOut.model_validate(r).model_dump(mode="json") for r in rows],
            "total": total,
        }
    )


@router.get("/{run_id}", response_model=R[dict], summary="Run 详情")
def get_run_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        detail = get_run_detail(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None
    return R.ok(
        {
            "run": RunOut.model_validate(detail["run"]).model_dump(mode="json"),
            "events": [
                RunEventOut.model_validate(e).model_dump(mode="json")
                for e in detail["events"]
            ],
            "artifacts": [
                RunArtifactOut.model_validate(a).model_dump(mode="json")
                for a in detail["artifacts"]
            ],
        }
    )


@router.get("/{run_id}/events", response_model=R[dict], summary="事件列表（断线补拉）")
def get_events_api(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        rows = get_events(
            db, run_id, current.project_id or 0, after_seq=after_seq, limit=limit
        )
    except RunNotFoundError:
        raise _not_found(run_id) from None
    return R.ok(
        {
            "items": [RunEventOut.model_validate(e).model_dump(mode="json") for e in rows],
            "last_seq": rows[-1].seq if rows else after_seq,
        }
    )


@router.get("/{run_id}/artifacts", response_model=R[dict], summary="Artifact 列表")
def get_artifacts_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        rows = get_artifacts(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None
    return R.ok(
        {"items": [RunArtifactOut.model_validate(a).model_dump(mode="json") for a in rows]}
    )


@router.get("/{run_id}/attempts", response_model=R[dict], summary="节点 attempt 列表（重试时间线）")
def get_attempts_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    """batch-340：返回每个节点的全部 StepAttempt（含失败 attempt 与重试）。"""
    try:
        run, node_attempts = get_run_attempts(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None
    return R.ok(
        {
            "run_id": run.id,
            "items": [
                {
                    "node_key": node.node_key,
                    "driver_key": node.driver_key,
                    "status": node.status,
                    "attempt_count": node.attempt_count,
                    "error_class": node.error_class,
                    "started_at": node.started_at,
                    "finished_at": node.finished_at,
                    "attempts": [
                        {
                            "attempt_no": attempt.attempt_no,
                            "status": attempt.status,
                            "started_at": attempt.started_at,
                            "finished_at": attempt.finished_at,
                            "error": attempt.error_json,
                            "output": attempt.output_summary_json,
                        }
                        for attempt in attempts
                    ],
                }
                for node, attempts in node_attempts
            ],
        }
    )


@router.get("/{run_id}/nodes", response_model=R[dict], summary="节点/Attempt/断言/产物聚合")
def get_run_nodes_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        run, items = get_run_nodes(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None

    def _assertion(row) -> dict:
        return {
            "id": row.id,
            "assertion_key": row.assertion_key,
            "type": row.assertion_type,
            "status": row.status,
            "schema_version": row.schema_version,
            "oracle_layer": row.oracle_layer,
            "oracle_ref": row.oracle_ref,
            "severity": row.severity,
            "expected": row.expected_json,
            "actual": row.actual_json,
            "actual_source": row.actual_source,
            "duration_ms": row.duration_ms,
            "timeout_ms": row.timeout_ms,
            "error": row.error_message,
            "artifact_refs": row.artifact_refs_json or [],
        }

    def _artifact(row) -> dict:
        return {
            "id": row.id,
            "artifact_type": row.artifact_type,
            "sha256": row.sha256,
            "size_bytes": row.size_bytes,
            "mime_type": row.mime_type,
            "redaction_status": row.redaction_status,
            "metadata": row.metadata_json or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    payload = []
    for item in items:
        node = item["node"]
        payload.append(
            {
                "node": {
                    "id": node.id,
                    "node_key": node.node_key,
                    "driver_key": node.driver_key,
                    "status": node.status,
                    "error_class": node.error_class,
                    "attempt_count": node.attempt_count,
                    "inputs": node.resolved_input_json or node.input_ref or {},
                    "outputs": node.outputs_json or node.output_ref or {},
                    "secret_keys": node.secret_keys_json or [],
                    "source_refs": node.source_refs_json or [],
                    "started_at": node.started_at.isoformat() if node.started_at else None,
                    "finished_at": node.finished_at.isoformat() if node.finished_at else None,
                },
                "attempts": [
                    {
                        "id": entry["attempt"].id,
                        "attempt_no": entry["attempt"].attempt_no,
                        "status": entry["attempt"].status,
                        "started_at": (
                            entry["attempt"].started_at.isoformat()
                            if entry["attempt"].started_at
                            else None
                        ),
                        "finished_at": (
                            entry["attempt"].finished_at.isoformat()
                            if entry["attempt"].finished_at
                            else None
                        ),
                        "error": entry["attempt"].error_json,
                        "output": entry["attempt"].output_summary_json,
                        "assertions": [_assertion(row) for row in entry["assertions"]],
                    }
                    for entry in item["attempts"]
                ],
                "artifacts": [_artifact(row) for row in item["artifacts"]],
            }
        )
    return R.ok(
        {
            "run_id": run.id,
            "status": run.status,
            "outcome": run.outcome,
            "nodes": payload,
        }
    )


@router.get("/{run_id}/assertions", response_model=R[dict], summary="断言结果列表")
def get_run_assertions_api(
    run_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        run, rows = get_run_assertions(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None
    items = []
    for entry in rows:
        assertion = entry["assertion"]
        items.append(
            {
                "node_key": entry["node_key"],
                "node_status": entry["node_status"],
                "attempt_no": entry["attempt_no"],
                "attempt_status": entry["attempt_status"],
                "assertion_key": assertion.assertion_key,
                "type": assertion.assertion_type,
                "status": assertion.status,
                "oracle_layer": assertion.oracle_layer,
                "oracle_ref": assertion.oracle_ref,
                "severity": assertion.severity,
                "expected": assertion.expected_json,
                "actual": assertion.actual_json,
                "actual_source": assertion.actual_source,
                "duration_ms": assertion.duration_ms,
                "error": assertion.error_message,
                "artifact_refs": assertion.artifact_refs_json or [],
            }
        )
    return R.ok(
        {
            "run_id": run.id,
            "status": run.status,
            "outcome": run.outcome,
            "items": items,
            "total": len(items),
        }
    )


def _sse_payload(event) -> str:
    """SSE 帧：带 `id`（断线重连 Last-Event-ID）与 `retry`（3s 重连）。"""
    data = json.dumps(
        RunEventOut.model_validate(event).model_dump(mode="json"), ensure_ascii=False
    )
    return f"id: {event.seq}\nretry: 3000\ndata: {data}\n\n"


def _parse_last_event_id(value: str | None) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


@router.get("/{run_id}/events/stream", summary="事件流（SSE 长连接）")
def stream_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    once: bool = Query(default=False),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        get_run(db, run_id, current.project_id or 0)
    except RunNotFoundError:
        raise _not_found(run_id) from None

    # 浏览器 EventSource 重连时携带 Last-Event-ID；与 after_seq 取较大值，确保不丢事件。
    start_seq = max(after_seq, _parse_last_event_id(last_event_id))

    def generate() -> Iterator[str]:
        seq = start_seq
        # 长连接：最多 30 分钟；Run 进入终态且已无新事件后主动关闭；每 15s 心跳一次。
        max_rounds = 1 if once else 1800
        for index in range(max_rounds):
            rows = list_events(db, run_id, after_seq=seq, limit=200)
            for row in rows:
                seq = row.seq
                yield _sse_payload(row)
            if once:
                break
            if not rows and index % 5 == 0:
                fresh = get_run(db, run_id, current.project_id or 0)
                if fresh.status in TERMINAL_STATUSES:
                    break
            if index and index % 15 == 0:
                yield ": keep-alive\n\n"
            db.expire_all()
            time.sleep(1)
        yield ": stream-end\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
