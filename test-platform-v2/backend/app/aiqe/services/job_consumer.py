"""M10-347：AIQE ExecutionJob 进程内消费者（解决 M9-R4）。

- 仅认领 payload 含 `node_run_id` 的 ExecutionJob（AIQE DAG 节点）；
- 原子认领（status pending → running + 租约），执行 `node_executor`，回写 `complete_node`；
- 默认关闭（`AIQE_INPROCESS_EXECUTOR_ENABLED=true` 时由 lifespan 启动线程），避免控制面意外执行。
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.redaction import redact_mapping
from app.aiqe.services import dag_scheduler, node_executor
from app.aiqe.services import lease as lease
from app.aiqe.services import preflight as preflight_service
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.execution_job import ExecutionJob

logger = logging.getLogger(__name__)

NODE_ID = "aiqe-inprocess"
LEASE_SECONDS = 300
MARKER = '"node_run_id"'
# 进程内消费者只处理 http 节点；playwright/appium 留给具备浏览器/设备的 runner 节点。
HTTP_DRIVERS = frozenset({"http", "httpx", "api", ""})

_stop = threading.Event()
_thread: threading.Thread | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _synthesize_graph(db: Session, run_id: str) -> dict:
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    return {"nodes": [{"key": row.node_key} for row in rows], "edges": []}


def claim_aiqe_jobs(db: Session, *, limit: int = 5) -> list[int]:
    """原子认领 AIQE 节点任务；仅 pending 且 payload 含 node_run_id。"""
    now = _now()
    rows = list(
        db.scalars(
            select(ExecutionJob)
            .where(
                ExecutionJob.status == "pending",
                ExecutionJob.payload_json.like(f"%{MARKER}%"),
            )
            .order_by(ExecutionJob.id)
            .limit(limit)
        )
    )
    claimed: list[int] = []
    for job in rows:
        try:
            driver = str(json.loads(job.payload_json or "{}").get("driver") or "").lower()
        except (TypeError, ValueError):
            driver = ""
        if driver not in HTTP_DRIVERS:
            continue
        # 先在内存里算出本次认领的 attempt，作为 fencing token 的唯一来源
        # （UPDATE 会让 ORM 对象同步为新值，不能再用 job.attempt+1 计算）。
        next_attempt = int(job.attempt or 0) + 1
        result = db.execute(
            update(ExecutionJob)
            .where(ExecutionJob.id == job.id, ExecutionJob.status == "pending")
            .values(
                status="running",
                node_id=NODE_ID,
                attempt=ExecutionJob.attempt + 1,
                claimed_at=now,
                started_at=now,
                heartbeat_at=now,
                lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
            )
        )
        if int(getattr(result, "rowcount", 0) or 0):
            claimed.append(int(job.id))
            # AUD-006：认领即提升节点 fencing token，旧 Worker 的迟到结果会被拒绝。
            try:
                payload = json.loads(job.payload_json or "{}")
            except (TypeError, ValueError):
                payload = {}
            node_run_id = str(payload.get("node_run_id") or "")
            if node_run_id:
                try:
                    lease.bump_fencing_token(db, node_run_id, token=next_attempt)
                except LookupError:
                    logger.warning("claimed job %s references missing node %s", job.id, node_run_id)
    db.commit()
    return claimed


def run_job(db: Session, job_id: int) -> dict:
    job = db.get(ExecutionJob, job_id)
    if job is None or job.status != "running":
        return {"job_id": job_id, "skipped": True}
    payload = json.loads(job.payload_json or "{}")
    run_id = str(payload.get("run_id") or "")
    node_run_id = str(payload.get("node_run_id") or "")
    node = db.get(NodeRun, node_run_id) if node_run_id else None
    run = db.get(TestRun, run_id) if run_id else None
    if node is None or run is None:
        job.status = "failed"
        job.error_message = "node_run/run not found"
        job.finished_at = _now()
        db.commit()
        return {"job_id": job_id, "status": "failed", "reason": "missing node/run"}

    graph = payload.get("graph") or _synthesize_graph(db, run_id)
    # AUD-006：持有过期/被顶替的租约时不得写入任何节点结果。
    lease_token = int(job.attempt or 0)
    try:
        lease.assert_current(
            db,
            node_run_id=node.id,
            fencing_token=lease_token,
            job_expires_at=job.lease_expires_at,
            job_id=job.id,
        )
    except (lease.StaleLeaseError, lease.LeaseExpired) as exc:
        job.status = "expired" if isinstance(exc, lease.LeaseExpired) else "failed"
        job.error_message = str(exc)[:500]
        job.finished_at = _now()
        db.commit()
        return {
            "job_id": job_id,
            "node": node.node_key,
            "skipped": True,
            "reason": type(exc).__name__,
        }
    # AUD-005：执行前预检；缺能力/Runner 直接 BLOCKED，不进入 Driver（避免假装执行）。
    preflight_result = preflight_service.preflight_node_run(db, node, run=run, graph=graph)
    if not preflight_result.allowed:
        detail = {"preflight": preflight_result.payload()}
        dag_scheduler.complete_node(
            db,
            run_id,
            node.node_key,
            "BLOCKED",
            graph,
            error_class="PREFLIGHT_BLOCKED",
            outputs=detail,
            fencing_token=lease_token,
        )
        job.status = "failed"
        job.result_json = json.dumps(detail, ensure_ascii=False, default=str)[:20000]
        job.summary = f"{node.node_key}:BLOCKED"
        job.error_message = "PREFLIGHT_BLOCKED"
        job.finished_at = _now()
        db.commit()
        return {
            "job_id": job_id,
            "node": node.node_key,
            "node_status": "BLOCKED",
            "job_status": job.status,
            "error_class": "PREFLIGHT_BLOCKED",
            "preflight": preflight_result.payload(),
        }

    if node.status == "READY":
        dag_scheduler.mark_running(db, run_id, node.node_key)

    result = node_executor.execute_node(node, db=db)
    # AUD-003：执行明细可能含 token/cookie，落库前统一脱敏（节点输出同一份）。
    safe_detail = redact_mapping(result.detail)
    dag_scheduler.complete_node(
        db,
        run_id,
        node.node_key,
        result.status,
        graph,
        error_class=result.error_class or None,
        outputs={"execution": safe_detail},
        fencing_token=lease_token,
    )
    job.status = "success" if result.status == "PASSED" else "failed"
    job.result_json = json.dumps(safe_detail, ensure_ascii=False, default=str)[:20000]
    job.summary = f"{node.node_key}:{result.status}"
    job.error_message = result.error_class
    job.finished_at = _now()
    db.commit()
    return {
        "job_id": job_id,
        "node": node.node_key,
        "node_status": result.status,
        "job_status": job.status,
        "error_class": result.error_class,
    }


def complete_from_report(
    db: Session,
    *,
    job_id: int,
    status: str,
    result: dict | None = None,
    error_message: str = "",
    fencing_token: int | None = None,
) -> dict:
    """外部 runner（浏览器/设备）上报后，把 AIQE 节点状态回写到 DAG。

    进程内消费者直接执行并回写；外部节点执行 UI/设备节点时必须走本函数，
    否则 ExecutionJob 成功但 NodeRun 永远 RUNNING。

    AUD-006：``fencing_token`` 必须等于节点当前租约 token，否则视为旧 Worker 迟到上报拒绝。
    """
    job = db.get(ExecutionJob, job_id)
    if job is None:
        return {"skipped": True, "reason": "job missing"}
    payload = json.loads(job.payload_json or "{}")
    run_id = str(payload.get("run_id") or "")
    node_run_id = str(payload.get("node_run_id") or "")
    node = db.get(NodeRun, node_run_id) if node_run_id else None
    run = db.get(TestRun, run_id) if run_id else None
    if node is None or run is None:
        return {"skipped": True, "reason": "node/run missing"}

    token = fencing_token if fencing_token is not None else int(job.attempt or 0)
    try:
        lease.assert_writable(db, node_run_id=node.id, fencing_token=token)
    except lease.StaleLeaseError as exc:
        return {
            "skipped": True,
            "reason": "STALE_LEASE",
            "detail": str(exc),
            "job_id": job_id,
        }

    graph = payload.get("graph") or _synthesize_graph(db, run_id)
    if node.status == "READY":
        dag_scheduler.mark_running(db, run_id, node.node_key)

    passed = str(status).lower() in {"completed", "success", "passed", "pass", "ok"}
    node_status = "PASSED" if passed else "FAILED"
    payload_result = redact_mapping(result or {})
    error_class = str(payload_result.get("error_class") or "").strip()
    if not passed and not error_class:
        error_class = (error_message or "")[:80] or "EXTERNAL_RUNNER_FAILED"

    dag_scheduler.complete_node(
        db,
        run_id,
        node.node_key,
        node_status,
        graph,
        error_class=error_class or None,
        outputs={"execution": payload_result},
        fencing_token=token,
    )
    db.commit()
    return {
        "job_id": job_id,
        "run_id": run_id,
        "node": node.node_key,
        "node_status": node_status,
        "error_class": error_class,
    }


def consume_once(*, limit: int = 5) -> int:
    db = SessionLocal()
    try:
        job_ids = claim_aiqe_jobs(db, limit=limit)
    finally:
        db.close()

    for job_id in job_ids:
        db = SessionLocal()
        try:
            run_job(db, job_id)
        except Exception as exc:  # 消费失败必须落库，不能悬挂 running
            db.rollback()
            job = db.get(ExecutionJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = f"{type(exc).__name__}: {exc}"[:500]
                job.finished_at = _now()
                db.commit()
            logger.exception("aiqe job %s failed", job_id)
        finally:
            db.close()
    return len(job_ids)


def start_aiqe_consumer(poll_seconds: float | None = None) -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    interval = float(poll_seconds or settings.aiqe_inprocess_poll_seconds)
    _stop.clear()

    def loop() -> None:
        while not _stop.is_set():
            try:
                consume_once()
            except Exception:  # 线程不能退出
                logger.exception("aiqe consumer loop error")
            _stop.wait(max(0.5, interval))

    _thread = threading.Thread(target=loop, name="aiqe-inprocess-executor", daemon=True)
    _thread.start()
    logger.info("aiqe in-process executor started")


def stop_aiqe_consumer() -> None:
    global _thread
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=5)
        _thread = None
