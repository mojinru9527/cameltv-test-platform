"""M10-347 + v1.4：AIQE ExecutionJob 进程内消费者。

- 仅认领 payload 含 `node_run_id` 的 ExecutionJob（AIQE DAG 节点）；
- 原子认领（status pending → running + 租约）；
- http / db 节点可在进程内执行；playwright/appium 只由具备浏览器/设备的 Runner 执行；
- 执行收口统一走 `execution_service`（断言、outputs、证据、事件）；
- 默认关闭（`AIQE_INPROCESS_EXECUTOR_ENABLED=true` 时由 lifespan 启动线程）。
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.aiqe.services import execution_service
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.execution_job import ExecutionJob

logger = logging.getLogger(__name__)

NODE_ID = "aiqe-inprocess"
LEASE_SECONDS = 300
MARKER = '"node_run_id"'
# 进程内消费者可执行的 driver；浏览器/设备节点仍必须由外部 Runner 执行。
INPROCESS_DRIVERS = frozenset(
    {"http", "httpx", "api", "", "db", "db_readonly", "database"}
)

_stop = threading.Event()
_thread: threading.Thread | None = None


def _now() -> datetime:
    return datetime.now(UTC)


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
        if driver not in INPROCESS_DRIVERS:
            continue
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
    db.commit()
    return claimed


def run_job(db: Session, job_id: int) -> dict:
    return execution_service.execute_inprocess_job(db, job_id)


def complete_from_report(
    db: Session,
    *,
    job_id: int,
    status: str,
    result: dict | None = None,
    error_message: str = "",
) -> dict:
    """外部 runner（浏览器/设备）上报后，把 AIQE 节点状态回写到 DAG。

    保留旧返回字段 `node_status`，内部走统一断言/证据/状态收口。
    """
    summary = execution_service.complete_from_external_report(
        db,
        job_id=job_id,
        status=status,
        result=result,
        error_message=error_message,
    )
    if summary.get("skipped"):
        return summary
    node_status = summary.get("status")
    summary.setdefault("node_status", node_status)
    summary.setdefault("node", summary.get("node_key"))
    summary.setdefault("error_class", "")
    return summary


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
