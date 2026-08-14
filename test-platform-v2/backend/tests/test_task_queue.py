"""Batch 181（FIX-173-P2-06）— 统一 TaskQueue 原语测试。

覆盖：
- atomic_claim：pending 认领、并发原子性（双会话仅一个成功）、stale 锁重认领、
  pending+新鲜锁跳过（reclaim_stale 语义）、extra_where 过滤
- reap_stale：失联 running → failed + 解锁；未超时不误伤；无锁列表降级
- finish_task：终态 + 解锁
- QueueWorkerLoop：start 幂等、kick、shutdown join
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.core.task_queue import (
    DEFAULT_STALE_SECONDS,
    QueueSpec,
    QueueWorkerLoop,
    atomic_claim,
    atomic_claim_by_id,
    finish_task,
    reap_stale,
    utcnow,
)
from app.models.ai_task import AiTask


def _make_sessions(tmp_path, name: str = "q.sqlite"):
    engine = create_engine(
        f"sqlite:///{tmp_path / name}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    return engine, factory


def _spec(**kw) -> QueueSpec:
    base = dict(
        model=AiTask,
        id_col="id",
        status_col="status",
        pending="pending",
        running="running",
        failed="failed",
        lock_by_col="locked_by",
        lock_at_col="locked_at",
        order_col="created_at",
        order_asc=True,
    )
    base.update(kw)
    return QueueSpec(**base)


def _task(factory, task_id: str, **kw) -> None:
    values = dict(
        id=task_id, task_type="generate", project_id=1, document_id=5,
        status="pending", progress=0, result_json="null", error="",
    )
    values.update(kw)
    s = factory()
    try:
        s.add(AiTask(**values))
        s.commit()
    finally:
        s.close()


class TestAtomicClaim:
    def test_claims_oldest_pending(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1")
        _task(factory, "t2")
        s = factory()
        try:
            claimed = atomic_claim(s, _spec(), worker_id="w1", stale_seconds=60)
            assert claimed is not None and claimed.id == "t1"
            assert claimed.status == "running"
            assert claimed.locked_by == "w1"
            assert claimed.locked_at is not None
            assert claimed.started_at is not None
        finally:
            s.close()
        engine.dispose()

    def test_second_session_cannot_claim_same(self, tmp_path):
        """并发原子性：两个会话认领同一任务，恰一个成功（TOCTOU 回归防护）。"""
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "race-1")
        sA, sB = factory(), factory()
        try:
            a = atomic_claim(sA, _spec(), worker_id="wA", stale_seconds=60)
            b = atomic_claim(sB, _spec(), worker_id="wB", stale_seconds=60)
            assert a is not None and a.id == "race-1"
            assert b is None
        finally:
            sA.close()
            sB.close()
        engine.dispose()

    def test_stale_pending_lock_reclaimable(self, tmp_path):
        """pending + 锁超时 → 可重认领（原 AI/DSH 语义）。"""
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1", locked_at=utcnow() - timedelta(minutes=10))
        s = factory()
        try:
            claimed = atomic_claim(s, _spec(), worker_id="w", stale_seconds=300)
            assert claimed is not None and claimed.id == "t1"
        finally:
            s.close()
        engine.dispose()

    def test_fresh_pending_lock_skipped(self, tmp_path):
        """pending + 新鲜锁 → 不可认领（reclaim_stale=True 默认语义）。"""
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1", locked_at=utcnow())
        s = factory()
        try:
            assert atomic_claim(s, _spec(), worker_id="w", stale_seconds=300) is None
        finally:
            s.close()
        engine.dispose()

    def test_reclaim_stale_disabled_claims_any_pending(self, tmp_path):
        """reclaim_stale=False（API 原语义）：仅按 status=pending 认领。"""
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1", locked_at=utcnow())
        s = factory()
        try:
            claimed = atomic_claim(
                s, _spec(), worker_id="w", stale_seconds=300, reclaim_stale=False
            )
            assert claimed is not None and claimed.id == "t1"
        finally:
            s.close()
        engine.dispose()

    def test_extra_where_filters_candidates(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "p1", project_id=1)
        _task(factory, "p2", project_id=2)
        s = factory()
        try:
            claimed = atomic_claim(
                s, _spec(), worker_id="w", stale_seconds=60,
                extra_where=AiTask.project_id == 2,
            )
            assert claimed is not None and claimed.id == "p2"
        finally:
            s.close()
        engine.dispose()

    def test_claim_by_id_specific(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1")
        _task(factory, "t2")
        s = factory()
        try:
            claimed = atomic_claim_by_id(s, _spec(), "t2", worker_id="w")
            assert claimed is not None and claimed.id == "t2"
            # 已认领后再按 id 认领失败
            assert atomic_claim_by_id(s, _spec(), "t2", worker_id="w2") is None
        finally:
            s.close()
        engine.dispose()


class TestReapStale:
    def test_reap_marks_stale_running_failed(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "zombie", status="running", locked_at=utcnow() - timedelta(hours=2))
        _task(factory, "fresh", status="running", locked_at=utcnow())
        s = factory()
        try:
            reaped = reap_stale(s, _spec(), stale_seconds=3600)
            assert reaped == 1
            zombie = s.get(AiTask, "zombie")
            fresh = s.get(AiTask, "fresh")
            assert zombie.status == "failed"
            assert zombie.locked_by == ""
            assert zombie.finished_at is not None
            assert "stale" in (zombie.error or "")
            assert fresh.status == "running"
        finally:
            s.close()
        engine.dispose()

    def test_reap_none_when_no_stale(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1", status="running", locked_at=utcnow())
        s = factory()
        try:
            assert reap_stale(s, _spec(), stale_seconds=3600) == 0
        finally:
            s.close()
        engine.dispose()

    def test_reap_fallback_started_at_when_no_lock_col(self, tmp_path):
        """无 locked_at 列的表按 started_at 降级判定（历史表兼容）。"""
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "old", status="running", started_at=utcnow() - timedelta(hours=2))
        _task(factory, "new", status="running", started_at=utcnow())
        s = factory()
        try:
            spec = _spec(lock_at_col="nonexistent_col")
            reaped = reap_stale(s, spec, stale_seconds=3600)
            assert reaped == 1
            assert s.get(AiTask, "old").status == "failed"
            assert s.get(AiTask, "new").status == "running"
        finally:
            s.close()
        engine.dispose()


class TestFinishTask:
    def test_finish_sets_status_and_releases_lock(self, tmp_path):
        engine, factory = _make_sessions(tmp_path)
        _task(factory, "t1")
        s = factory()
        try:
            claimed = atomic_claim(s, _spec(), worker_id="w", stale_seconds=60)
            finish_task(s, claimed, _spec(), status="done", progress=100)
            s.expire_all()
            row = s.get(AiTask, "t1")
            assert row.status == "done"
            assert row.locked_by == ""
            assert row.finished_at is not None
            assert row.progress == 100
        finally:
            s.close()
        engine.dispose()


class TestQueueWorkerLoop:
    def test_start_kick_shutdown(self):
        ticks = []
        loop = QueueWorkerLoop(name="test-loop", poll_interval=0.05, on_tick=lambda: ticks.append(1))
        loop.start()
        loop.start()  # 幂等
        loop.kick()
        deadline = time.time() + 2
        while not ticks and time.time() < deadline:
            time.sleep(0.02)
        assert ticks, "worker 应至少 tick 一次"
        loop.shutdown(timeout=2)
        assert loop._thread is None
        assert not loop._thread  # noqa: B016 - 关闭后线程置空

    def test_shutdown_joins_thread(self):
        loop = QueueWorkerLoop(name="test-loop2", poll_interval=10, on_tick=lambda: None)
        loop.start()
        thread = loop._thread
        assert thread is not None and thread.is_alive()
        loop.shutdown(timeout=2)
        assert not thread.is_alive()
        assert loop._thread is None


class TestAgentQueueIntegration:
    """Agent 队列（Batch 181）：认领原子性与 stale 回收（原实现无回收）。"""

    def _agent_spec(self):
        from app.models.knowledge import AgentQueueItem

        return QueueSpec(
            model=AgentQueueItem,
            id_col="id",
            status_col="status",
            pending="pending",
            running="running",
            failed="failed",
            lock_by_col="locked_by",
            lock_at_col="locked_at",
            order_col="id",
            order_asc=True,
            extra_order=(("priority", True),),
        )

    def test_double_claim_prevented(self, tmp_path):
        """双会话认领同一 Agent 队列项，恰一个成功（TOCTOU 回归防护）。"""
        from app.models.knowledge import AgentQueueItem

        engine, factory = _make_sessions(tmp_path, "agent.sqlite")
        s0 = factory()
        s0.add(AgentQueueItem(project_id=1, agent_type="a", status="pending", priority=10))
        s0.commit()
        s0.close()

        sA, sB = factory(), factory()
        try:
            a = atomic_claim(sA, self._agent_spec(), worker_id="wA")
            b = atomic_claim(sB, self._agent_spec(), worker_id="wB")
            assert a is not None
            assert b is None
        finally:
            sA.close()
            sB.close()
        engine.dispose()

    def test_agent_reap_stale(self, tmp_path):
        """Agent 队列失联回收：running + 锁超时 → failed。"""
        from app.models.knowledge import AgentQueueItem

        engine, factory = _make_sessions(tmp_path, "agent-reap.sqlite")
        s0 = factory()
        s0.add(AgentQueueItem(
            project_id=1, agent_type="a", status="running",
            locked_at=utcnow() - timedelta(hours=2), locked_by="dead",
        ))
        s0.commit()
        s0.close()

        s = factory()
        try:
            reaped = reap_stale(s, self._agent_spec(), stale_seconds=3600)
            assert reaped == 1
            row = s.get(AgentQueueItem, 1)
            assert row.status == "failed"
            assert row.locked_by == ""
        finally:
            s.close()
        engine.dispose()


class TestUiRunStaleReap:
    """UI run 失联回收（Batch 181 新增，原实现无回收）。"""

    def test_ui_run_spec_reaps_stale(self, tmp_path):
        from app.models.ui_test import UiTestJob, UiTestRun

        engine, factory = _make_sessions(tmp_path, "ui.sqlite")
        s0 = factory()
        job = UiTestJob(project_id=1, name="j1")
        s0.add(job)
        s0.commit()
        s0.add(UiTestRun(
            job_id=job.id, status="running",
            started_at=utcnow() - timedelta(hours=2),
            locked_at=utcnow() - timedelta(hours=2), locked_by="dead-runner",
        ))
        s0.add(UiTestRun(
            job_id=job.id, status="running",
            started_at=utcnow(), locked_at=utcnow(), locked_by="live-runner",
        ))
        s0.commit()
        s0.close()

        spec = QueueSpec(
            model=UiTestRun,
            status_col="status",
            pending="pending",
            running="running",
            failed="fail",
            lock_by_col="locked_by",
            lock_at_col="locked_at",
        )
        s = factory()
        try:
            reaped = reap_stale(s, spec, stale_seconds=3600)
            assert reaped == 1
            runs = s.query(UiTestRun).order_by(UiTestRun.id).all()
            stale, fresh = runs[0], runs[1]
            assert stale.status == "fail"
            assert stale.locked_by == ""
            assert fresh.status == "running"
            assert fresh.locked_by == "live-runner"
        finally:
            s.close()
        engine.dispose()
