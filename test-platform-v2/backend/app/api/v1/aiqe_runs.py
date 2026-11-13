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
from app.aiqe.services.run_state import TERMINAL_STATUSES
from app.aiqe.services.run_query_service import (
    RunNotFoundError,
    get_artifacts,
    get_events,
    get_run,
    get_run_attempts,
    get_run_detail,
    list_runs,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.aiqe_run import RunArtifactOut, RunEventOut, RunOut
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/runs", tags=["aiqe-runs"])


def _not_found(run_id: str) -> APIException:
    return APIException(code=404, msg=f"Run 不存在: {run_id}", http_status=404)


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
