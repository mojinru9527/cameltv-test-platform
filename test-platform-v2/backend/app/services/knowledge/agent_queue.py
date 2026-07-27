"""Agent 任务队列（M5）—— DB 持久化 + 并发控制 + 优先级 + 重试。

设计：
- 每个项目最多 2 个 Agent 并发执行
- 优先级：手动触发 (10) > 自动触发 (0)
- 失败自动重试 1 次（间隔 30s）
- 队列项可手动取消（仅 pending 状态）
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import AgentQueueItem
from app.services.knowledge.agent_orchestrator import run_agent_in_new_session

logger = logging.getLogger("knowledge.queue")

# 每个项目最大并发 Agent 数
_MAX_CONCURRENT_PER_PROJECT = 2

# 优先级常量
PRIORITY_MANUAL = 10
PRIORITY_AUTO = 0

# 队列处理器间隔（秒）
_PROCESS_INTERVAL = 3.0

# 重试间隔（秒）
_RETRY_DELAY = 30

# 全局处理器状态
_processor_started = False
_processor_lock = threading.Lock()

_SQLITE_LOCK_RETRY_ATTEMPTS = 3
_SQLITE_LOCK_RETRY_BASE_DELAY = 0.05


class QueueWriteBusy(RuntimeError):
    """Raised after bounded retries exhaust transient SQLite writer contention."""


def _is_sqlite_locked(exc: OperationalError) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "database is locked",
            "database table is locked",
            "database schema is locked",
        )
    )


# ── 队列 CRUD ──

def enqueue(
    db: Session,
    project_id: int,
    agent_type: str,
    *,
    trigger_type: str = "manual",
    user_input: str = "",
    params: dict | None = None,
    operator_id: int = 0,
    priority: int | None = None,
) -> AgentQueueItem:
    """Add an Agent task using the caller-owned session and transaction."""
    if priority is None:
        priority = PRIORITY_MANUAL if trigger_type == "manual" else PRIORITY_AUTO

    for attempt in range(_SQLITE_LOCK_RETRY_ATTEMPTS):
        item = AgentQueueItem(
            project_id=project_id,
            agent_type=agent_type,
            trigger_type=trigger_type,
            priority=priority,
            input_json=json.dumps({"user_input": user_input, "params": params or {}}, ensure_ascii=False),
            status="pending",
            operator_id=operator_id,
        )
        db.add(item)
        try:
            # Flush executes the INSERT while leaving commit ownership with the
            # request handler, so all request-side writes share one transaction.
            db.flush()
            return item
        except OperationalError as exc:
            db.rollback()
            if not _is_sqlite_locked(exc):
                raise
            if attempt == _SQLITE_LOCK_RETRY_ATTEMPTS - 1:
                raise QueueWriteBusy("agent queue is temporarily busy") from exc
            delay = _SQLITE_LOCK_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Agent queue write locked; retrying in %.2fs (%s/%s)",
                delay,
                attempt + 1,
                _SQLITE_LOCK_RETRY_ATTEMPTS,
            )
            time.sleep(delay)

    raise QueueWriteBusy("agent queue is temporarily busy")


def commit_queue_write(db: Session) -> None:
    """Commit a caller-owned queue write without leaking SQLite lock errors."""
    try:
        db.commit()
    except OperationalError as exc:
        db.rollback()
        if _is_sqlite_locked(exc):
            raise QueueWriteBusy("agent queue is temporarily busy") from exc
        raise


def cancel_queue_item(db, item_id: int, project_id: int) -> bool:
    """取消 pending 状态的队列项。返回是否成功。"""
    item = db.get(AgentQueueItem, item_id)
    if not item or item.project_id != project_id:
        return False
    if item.status != "pending":
        return False
    item.status = "cancelled"
    item.finished_at = datetime.now()
    return True


def get_queue_stats(db, project_id: int) -> dict:
    """获取队列统计。"""
    def _count(status: str) -> int:
        return db.scalar(
            select(func.count(AgentQueueItem.id)).where(
                AgentQueueItem.project_id == project_id,
                AgentQueueItem.status == status,
            )
        ) or 0

    return {
        "pending": _count("pending"),
        "running": _count("running"),
        "completed": _count("completed"),
        "failed": _count("failed"),
    }


def list_queue_items(
    db,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AgentQueueItem], int]:
    """分页列出队列项。"""
    stmt = select(AgentQueueItem).where(AgentQueueItem.project_id == project_id)
    cnt = select(func.count(AgentQueueItem.id)).where(AgentQueueItem.project_id == project_id)
    if status:
        stmt = stmt.where(AgentQueueItem.status == status)
        cnt = cnt.where(AgentQueueItem.status == status)

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(AgentQueueItem.priority.desc(), AgentQueueItem.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


# ── 队列处理器（后台线程） ──

def _process_queue_once() -> int:
    """扫描所有项目的 pending 队列项，按并发限制调度执行。返回本次调度的任务数。"""
    db = SessionLocal()
    dispatched = 0
    try:
        # 获取有 pending 任务的项目列表
        projects = list(
            db.scalars(
                select(AgentQueueItem.project_id.distinct()).where(
                    AgentQueueItem.status == "pending",
                )
            ).all()
        )

        for pid in projects:
            # 统计该项目当前 running 数
            running_count = db.scalar(
                select(func.count(AgentQueueItem.id)).where(
                    AgentQueueItem.project_id == pid,
                    AgentQueueItem.status == "running",
                )
            ) or 0

            available = _MAX_CONCURRENT_PER_PROJECT - running_count
            if available <= 0:
                continue

            # 取优先级最高的 pending 项
            pending = list(
                db.scalars(
                    select(AgentQueueItem)
                    .where(
                        AgentQueueItem.project_id == pid,
                        AgentQueueItem.status == "pending",
                    )
                    .order_by(AgentQueueItem.priority.desc(), AgentQueueItem.id.asc())
                    .limit(available)
                ).all()
            )

            for item in pending:
                # 标记为 running
                item.status = "running"
                item.started_at = datetime.now()
                db.commit()

                # 在后台线程中执行 Agent（不阻塞队列扫描）
                t = threading.Thread(
                    target=_execute_queue_item,
                    args=(item.id, pid),
                    daemon=True,
                )
                t.start()
                dispatched += 1

    except Exception:
        logger.exception("Queue processor error")
        db.rollback()
    finally:
        db.close()

    return dispatched


def _execute_queue_item(item_id: int, project_id: int) -> None:
    """在独立 Session 中执行一个队列项。完成后更新状态。"""
    db = SessionLocal()
    try:
        item = db.get(AgentQueueItem, item_id)
        if not item or item.status != "running":
            return

        input_data = {}
        try:
            input_data = json.loads(item.input_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass

        # 调用编排引擎
        result = run_agent_in_new_session(
            project_id=project_id,
            agent_type=item.agent_type,
            user_input=input_data.get("user_input", ""),
            params=input_data.get("params", {}),
            operator_id=item.operator_id,
        )

        item = db.get(AgentQueueItem, item_id)  # 重新获取（避免过期）
        if not item:
            return

        if result.get("status") == "success":
            item.status = "completed"
            item.finished_at = datetime.now()
        else:
            # 重试逻辑
            if item.retry_count < item.max_retries:
                item.retry_count += 1
                item.error_message = result.get("error", "")
                item.status = "pending"
                logger.info("Queue item %s retry %s/%s", item_id, item.retry_count, item.max_retries)
            else:
                item.status = "failed"
                item.error_message = result.get("error", "执行失败（已达最大重试次数）")
                item.finished_at = datetime.now()

        db.commit()

    except Exception:
        logger.exception("Queue item %s execution failed", item_id)
        try:
            item = db.get(AgentQueueItem, item_id)
            if item:
                if item.retry_count < item.max_retries:
                    item.retry_count += 1
                    item.status = "pending"
                else:
                    item.status = "failed"
                    item.error_message = "执行异常"
                    item.finished_at = datetime.now()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _queue_loop() -> None:
    """后台队列处理循环（运行在守护线程中）。"""
    logger.info("Agent queue processor started")
    while True:
        try:
            _process_queue_once()
        except Exception:
            logger.exception("Queue loop iteration error")
        time.sleep(_PROCESS_INTERVAL)


def ensure_processor_running() -> None:
    """确保队列处理器已启动（幂等）。"""
    global _processor_started
    with _processor_lock:
        if not _processor_started:
            t = threading.Thread(target=_queue_loop, daemon=True, name="agent-queue-processor")
            t.start()
            _processor_started = True
            logger.info("Agent queue processor thread started")
