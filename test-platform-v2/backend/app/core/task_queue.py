"""统一认领式任务队列原语（FIX-173-P2-06 / Batch 181）。

六套认领式队列（API 批量 / AI / DSH / 蓝湖证据包 / Agent / UI run）此前各自为政：
认领方式 3 种（skip_locked、UPDATE-rowcount、非原子 SELECT→改→commit）、
锁字段 3 套、失联回收仅 2 套具备。本模块提供统一原语：

- `QueueSpec`：队列契约（模型、状态词表、锁列、排序）。
- `atomic_claim` / `atomic_claim_by_id`：条件 UPDATE + rowcount 校验的原子认领，
  兼容 SQLite 单写者与 PostgreSQL 多副本，消除 TOCTOU（对比 scheduler.py:34 的
  with_for_update 范式，本实现更可移植且无需方言分支）。
- `reap_stale`：running 且活性信号（默认 locked_at）超时 → failed + 解锁，
  消除「任务永久卡 running」的僵尸任务。
- `finish_task`：置终态并清锁。
- `QueueWorkerLoop`：线程 + 唤醒事件 + 轮询间隔 + 幂等 start/shutdown，
  统一各队列的后台循环骨架。

约定：
- 时间统一使用 **naive UTC**（`datetime.now(timezone.utc).replace(tzinfo=None)`），
  与 SQLite 存储语义一致；所有活性比较在 SQL 层完成，不做 Python 层 aware/naive 混比。
- 各队列的状态词表与 execute 处理器保持域内原样（状态枚举统一属 P1-06，不在本批）。
- 队列写入口若持锁失败（rowcount==0），调用方不得执行任务体，直接返回 None。
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 默认失联阈值：30 分钟（与 batch-174 api_task_worker.STALE_LOCK_SECONDS 对齐）
DEFAULT_STALE_SECONDS = 30 * 60


def utcnow() -> datetime:
    """naive UTC now（SQLite 友好）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class QueueSpec:
    """一张队列表的契约描述。

    Args:
        model: ORM 模型类。
        id_col: 主键列名（默认 "id"）。
        status_col: 状态列名（默认 "status"）。
        pending / running / failed: 该队列的状态词表值。
        lock_by_col / lock_at_col: 持锁者 / 持锁时间列（Batch 181 前部分表缺失，
            由 `20260816_b181_task_queue_locks` 迁移补齐；本类对缺失列自动降级）。
        liveness_col: 失联判定活性列；None 时回落 lock_at_col
            （证据包传 "heartbeat_at" 并由 job_runner 心跳持续更新）。
        order_col / order_asc: 认领顺序（FIFO 默认 id 升序）。
        extra_order: 追加排序 `(列名, 是否降序)` 列表（Agent 队列 priority desc）。
    """

    model: type
    id_col: str = "id"
    status_col: str = "status"
    pending: str = "pending"
    running: str = "running"
    failed: str = "failed"
    lock_by_col: str = "locked_by"
    lock_at_col: str = "locked_at"
    liveness_col: str | None = None
    order_col: str = "id"
    order_asc: bool = True
    extra_order: Sequence[tuple[str, bool]] = field(default_factory=tuple)

    @property
    def liveness(self) -> str:
        return self.liveness_col or self.lock_at_col


def _has_col(spec: QueueSpec, col: str) -> bool:
    return col in spec.model.__table__.columns


def _stale_before(stale_seconds: int) -> datetime:
    return utcnow() - timedelta(seconds=max(1, stale_seconds))


# ═══════════════════════════════════════════════════════════════════
# 原子认领
# ═══════════════════════════════════════════════════════════════════

def atomic_claim(
    db: Session,
    spec: QueueSpec,
    *,
    worker_id: str,
    stale_seconds: int = DEFAULT_STALE_SECONDS,
    extra_where: Any = None,
    reclaim_stale: bool = True,
) -> Any | None:
    """原子认领最早一条可认领任务（pending 或 stale 锁可重认领）。

    算法（SQLite/PG 通用）：
    1. 先回收失联 running（reap_stale），避免僵尸阻塞；
    2. SELECT 候选 id（status=pending，可选 extra_where，按 spec 排序 LIMIT 1）；
       `reclaim_stale=True`（默认）时追加「锁为空或锁已过期」条件——
       AI/DSH 队列原语义：pending 但锁仍新鲜的任务不可被认领（持有者可能仍在处理）；
       API 队列原语义无此条件，传 False 保持精确兼容。
    3. 条件 UPDATE ... WHERE id=候选 AND status=pending（携带锁列与 started_at 兜底）；
    4. rowcount==0 → 被并发方抢走，返回 None；否则 refresh 返回行。

    返回的模型行已持锁（status=running + lock_by/lock_at），调用方必须
    在 finally 中保证 finish_task 或异常置 failed，不得静默丢弃。
    """
    reap_stale(db, spec, stale_seconds=stale_seconds)

    order_col = getattr(spec.model, spec.order_col)
    stmt = (
        select(spec.model.id)
        .where(getattr(spec.model, spec.status_col) == spec.pending)
        .order_by(*_order_clauses(spec, order_col))
        .limit(1)
    )
    if extra_where is not None:
        stmt = stmt.where(extra_where)
    if reclaim_stale and _has_col(spec, spec.lock_at_col):
        lock_at = getattr(spec.model, spec.lock_at_col)
        stmt = stmt.where(or_(lock_at.is_(None), lock_at < _stale_before(stale_seconds)))
    candidate = db.scalar(stmt)
    if candidate is None:
        db.rollback()
        return None

    row = _claim_by_id(db, spec, candidate, worker_id=worker_id)
    if row is None:
        db.rollback()
        return None
    return row


def atomic_claim_by_id(
    db: Session,
    spec: QueueSpec,
    row_id: Any,
    *,
    worker_id: str,
) -> Any | None:
    """原子认领指定 id 的任务（UI run 路径：先选 pending 再按 id 认领）。"""
    row = _claim_by_id(db, spec, row_id, worker_id=worker_id)
    if row is None:
        db.rollback()
    return row


def _claim_by_id(db: Session, spec: QueueSpec, row_id: Any, *, worker_id: str) -> Any | None:
    now = utcnow()
    values: dict[str, Any] = {
        getattr(spec.model, spec.status_col).key: spec.running,
    }
    if _has_col(spec, spec.lock_by_col):
        values[getattr(spec.model, spec.lock_by_col).key] = worker_id
    if _has_col(spec, spec.lock_at_col):
        values[getattr(spec.model, spec.lock_at_col).key] = now

    result = db.execute(
        update(spec.model)
        .where(
            getattr(spec.model, spec.id_col) == row_id,
            getattr(spec.model, spec.status_col) == spec.pending,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if result.rowcount != 1:
        return None
    row = db.get(spec.model, row_id)
    if row is not None and _has_col(spec, "started_at") and getattr(row, "started_at") is None:
        # 仅当尚未开始才写入 started_at（幂等恢复场景不覆盖原值）
        setattr(row, "started_at", now)
        db.commit()
    return row


def _order_clauses(spec: QueueSpec, order_col) -> list:
    clauses = [order_col.asc() if spec.order_asc else order_col.desc()]
    for col_name, desc in spec.extra_order:
        col = getattr(spec.model, col_name)
        clauses.append(col.desc() if desc else col.asc())
    return clauses


# ═══════════════════════════════════════════════════════════════════
# 失联回收
# ═══════════════════════════════════════════════════════════════════

def reap_stale(
    db: Session,
    spec: QueueSpec,
    *,
    stale_seconds: int = DEFAULT_STALE_SECONDS,
    failed_value: str | None = None,
    error_message: str | None = None,
) -> int:
    """回收失联任务：running 且活性信号超时 → failed + 释放锁。

    活性信号 = `spec.liveness`（默认 locked_at）。对缺失锁列的历史表自动降级：
    无 locked_at 时按 started_at 判定；两列皆无则跳过回收（返回 0）。
    返回回收条数。
    """
    liveness_col = spec.liveness if _has_col(spec, spec.liveness) else (
        "started_at" if _has_col(spec, "started_at") else None
    )
    if liveness_col is None:
        return 0

    cutoff = _stale_before(stale_seconds)
    liveness = getattr(spec.model, liveness_col)
    values: dict[str, Any] = {
        getattr(spec.model, spec.status_col).key: failed_value or spec.failed,
    }
    if _has_col(spec, "finished_at"):
        values[getattr(spec.model, "finished_at").key] = utcnow()
    if _has_col(spec, spec.lock_by_col):
        values[getattr(spec.model, spec.lock_by_col).key] = ""
    msg = error_message or (
        f"stale: 执行器失联超过 {stale_seconds // 60} 分钟，已回收（Batch 181）"
    )
    # 错误列名回落：error_message / error（各表命名不一）
    for err_col in ("error_message", "error"):
        if _has_col(spec, err_col):
            values[getattr(spec.model, err_col).key] = msg
            break

    result = db.execute(
        update(spec.model)
        .where(
            getattr(spec.model, spec.status_col) == spec.running,
            liveness.isnot(None),
            liveness < cutoff,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    reaped = int(result.rowcount or 0)
    if reaped:
        db.commit()
        logger.warning("[task-queue] %s: reaped %s stale task(s)", spec.model.__name__, reaped)
    else:
        db.rollback()
    return reaped


# ═══════════════════════════════════════════════════════════════════
# 收尾与解锁
# ═══════════════════════════════════════════════════════════════════

def finish_task(
    db: Session,
    row: Any,
    spec: QueueSpec,
    *,
    status: str,
    **extra: Any,
) -> None:
    """置任务终态并释放锁（清空 locked_by；locked_at 保留历史）。

    Args:
        status: 终态值（success/failed/cancelled/done 等，按队列词表）。
        extra: 需一并写回的字段（如 error_message、finished_at 由本函数自动置）。
    """
    setattr(row, spec.status_col, status)
    if _has_col(spec, "finished_at"):
        setattr(row, "finished_at", utcnow())
    if _has_col(spec, spec.lock_by_col):
        setattr(row, spec.lock_by_col, "")
    for key, value in extra.items():
        setattr(row, key, value)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# 后台循环骨架
# ═══════════════════════════════════════════════════════════════════

class QueueWorkerLoop:
    """后台轮询循环：唤醒事件 + 轮询间隔 + 幂等 start/shutdown。

    on_tick 在每次唤醒/超时后执行；异常被捕获记录后继续循环（worker 不崩）。
    各队列通过 `kick()` 在提交任务后立即唤醒，缩短空转延迟。
    """

    def __init__(
        self,
        name: str,
        *,
        poll_interval: float = 2.0,
        on_tick: Callable[[], None],
    ) -> None:
        self.name = name
        self.poll_interval = poll_interval
        self.on_tick = on_tick
        self._thread: threading.Thread | None = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop,
                daemon=True,
                name=self.name,
            )
            self._thread.start()
            logger.info("[%s] worker loop started", self.name)

    def kick(self) -> None:
        self._wake.set()

    def shutdown(self, timeout: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._stop.set()
            self._wake.set()
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning("[%s] worker did not stop within %.1fs", self.name, timeout)
            return
        with self._lock:
            if self._thread is thread:
                self._thread = None
                logger.info("[%s] worker loop stopped", self.name)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=self.poll_interval)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                self.on_tick()
            except Exception:  # noqa: BLE001 - worker 循环不允许崩溃
                logger.exception("[%s] tick error", self.name)


def new_worker_id(prefix: str) -> str:
    """生成进程级 worker 标识（写 locked_by）。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
