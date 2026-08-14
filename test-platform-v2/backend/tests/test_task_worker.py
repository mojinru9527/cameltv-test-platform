"""Unit tests for task_worker service — uses db_session fixture.

Tests cover poll logic, status transitions, and semaphore existence.
Does NOT execute real API/UI tests — those require external servers.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from unittest.mock import patch


# ── Helper: prevent worker code from closing the test session ──

class _NoCloseSession:
    """Wrapper that delegates everything to inner session except close()."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def close(self):
        pass  # do NOT close the test session


# ═══════════════════════════════════════════════════════════
# Semaphore existence
# ═══════════════════════════════════════════════════════════

class TestSemaphores:
    def test_ui_semaphore_exists(self):
        from app.services.task_worker import _semaphore_ui
        assert isinstance(_semaphore_ui, threading.Semaphore)
        assert _semaphore_ui._value >= 1

    def test_api_semaphore_removed_batch174(self):
        """Batch 174（FIX-173-P0-01）：API 批量任务已移交 api_task_worker 唯一处理，
        task_worker 不再持有 API 信号量。"""
        from app.services import task_worker
        assert not hasattr(task_worker, "_semaphore_api")


# ═══════════════════════════════════════════════════════════
# API task poll — Batch 174 移除（FIX-173-P0-01）
# ═══════════════════════════════════════════════════════════

class TestProcessApiTasksRemoved:
    """Batch 174：task_worker 的 API 处理分支已整体移除。

    此前 APScheduler 轮询（task_worker）与 api_task_worker 守护线程并行认领同一
    pending 任务，且认领后 status 已置 running，导致 task_worker._run_api_task 的
    `status not in ("pending",)` 守卫直接 return —— 任务永久卡 running 无结果。
    API 批量任务现在由 api_task_worker._processor_loop 唯一认领执行。
    """

    def test_process_api_tasks_function_removed(self):
        from app.services import task_worker
        assert not hasattr(task_worker, "_process_api_tasks")
        assert not hasattr(task_worker, "_run_api_task")

    def test_poll_and_execute_does_not_touch_api_tasks(self, db_session):
        """poll_and_execute 只处理 UI runs 与蓝湖证据包，绝不认领 API 任务。"""
        from app.models.api_asset import ApiExecutionTask
        from app.services import task_worker

        task = ApiExecutionTask(
            project_id=1, task_id="T-PENDING", name="Pending",
            total=1, status="pending",
        )
        db_session.add(task)
        db_session.commit()

        with patch("app.core.db.SessionLocal", return_value=_NoCloseSession(db_session)), \
             patch("app.services.api_task_worker.claim_next_task") as mock_claim, \
             patch("app.services.lanhu_evidence.worker.poll_and_execute_evidence_jobs"):
            task_worker.poll_and_execute()

        # API 认领绝不被 task_worker 触发（双 Worker 竞态根因已被移除）
        mock_claim.assert_not_called()
        db_session.refresh(task)
        assert task.status == "pending"  # 任务保持 pending，等待 api_task_worker


# ═══════════════════════════════════════════════════════════
# UI run poll — _process_ui_runs
# ═══════════════════════════════════════════════════════════

class TestProcessUiRuns:
    def test_picks_up_pending_run(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun
        from app.services.task_worker import _process_ui_runs

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="idle", created_at=now)
        db_session.add(job)
        db_session.flush()

        run = UiTestRun(job_id=job.id, status="pending", started_at=now)
        db_session.add(run)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_ui_test") as mock_run:
            _process_ui_runs()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert call_args[0] == run.id
        assert call_args[1] == run.job_id

    def test_skips_running_ui_runs(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun
        from app.services.task_worker import _process_ui_runs

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="idle", created_at=now)
        db_session.add(job)
        db_session.flush()

        run = UiTestRun(job_id=job.id, status="running", started_at=now)
        db_session.add(run)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_ui_test") as mock_run:
            _process_ui_runs()

        mock_run.assert_not_called()

    def test_skips_done_ui_runs(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun
        from app.services.task_worker import _process_ui_runs

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="done", created_at=now)
        db_session.add(job)
        db_session.flush()

        run = UiTestRun(job_id=job.id, status="done", started_at=now)
        db_session.add(run)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_ui_test") as mock_run:
            _process_ui_runs()

        mock_run.assert_not_called()

    def test_empty_ui_queue_handled(self, db_session):
        from app.services.task_worker import _process_ui_runs

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_ui_test") as mock_run:
            _process_ui_runs()

        mock_run.assert_not_called()

    def test_ui_semaphore_released_after_error(self, db_session):
        from app.services.task_worker import _process_ui_runs, _semaphore_ui

        initial = _semaphore_ui._value

        with patch("app.core.db.SessionLocal", side_effect=RuntimeError("boom")):
            try:
                _process_ui_runs()
            except RuntimeError:
                pass

        assert _semaphore_ui._value == initial, "UI semaphore should be released after error"


# ═══════════════════════════════════════════════════════════
# poll_and_execute — orchestration
# ═══════════════════════════════════════════════════════════

class TestPollAndExecute:
    def test_calls_ui_and_evidence_processors(self):
        from app.services import task_worker

        with patch.object(task_worker, "_process_ui_runs") as mock_ui, \
             patch("app.services.lanhu_evidence.worker.poll_and_execute_evidence_jobs") as mock_evidence:
            task_worker.poll_and_execute()
            mock_ui.assert_called_once()
            mock_evidence.assert_called_once()
