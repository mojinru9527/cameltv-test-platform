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
    def test_api_semaphore_exists(self):
        from app.services.task_worker import _semaphore_api
        assert isinstance(_semaphore_api, threading.Semaphore)
        assert _semaphore_api._value >= 1

    def test_ui_semaphore_exists(self):
        from app.services.task_worker import _semaphore_ui
        assert isinstance(_semaphore_ui, threading.Semaphore)
        assert _semaphore_ui._value >= 1


# ═══════════════════════════════════════════════════════════
# API task poll — _process_api_tasks
# ═══════════════════════════════════════════════════════════

class TestProcessApiTasks:
    def test_picks_up_pending_task(self, db_session):
        """A pending task should be picked up and submitted to _run_api_task."""
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        task = ApiExecutionTask(
            project_id=1, task_id="T-PENDING", name="Pending",
            total=1, status="pending",
        )
        db_session.add(task)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert call_args[0] == task.id

    def test_skips_when_no_pending(self, db_session):
        """When no pending tasks exist, nothing should happen."""
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        task = ApiExecutionTask(
            project_id=1, task_id="T-DONE", name="Done",
            total=1, status="success",
        )
        db_session.add(task)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_not_called()

    def test_skips_running_tasks(self, db_session):
        """Tasks in 'running' status should not be picked up."""
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        task = ApiExecutionTask(
            project_id=1, task_id="T-RUNNING", name="Running",
            total=1, status="running",
        )
        db_session.add(task)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_not_called()

    def test_skips_failed_tasks(self, db_session):
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        task = ApiExecutionTask(
            project_id=1, task_id="T-FAILED", name="Failed",
            total=1, status="failed",
        )
        db_session.add(task)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_not_called()

    def test_skips_cancelled_tasks(self, db_session):
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        task = ApiExecutionTask(
            project_id=1, task_id="T-CANCEL", name="Cancelled",
            total=1, status="cancelled",
        )
        db_session.add(task)
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_not_called()

    def test_empty_queue_handled(self, db_session):
        """No tasks at all should not crash."""
        from app.services.task_worker import _process_api_tasks

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_not_called()

    def test_picks_oldest_first(self, db_session):
        """Should pick the oldest pending task (by created_at ASC)."""
        from datetime import timedelta
        from app.models.api_asset import ApiExecutionTask
        from app.services.task_worker import _process_api_tasks

        now = datetime.now(timezone.utc)
        older = ApiExecutionTask(
            project_id=1, task_id="T-OLDER", name="Older",
            total=1, status="pending",
            created_at=now - timedelta(hours=2),
        )
        newer = ApiExecutionTask(
            project_id=1, task_id="T-NEWER", name="Newer",
            total=1, status="pending",
            created_at=now,
        )
        db_session.add_all([newer, older])  # deliberate insert order swap
        db_session.commit()

        wrapped = _NoCloseSession(db_session)
        with patch("app.core.db.SessionLocal", return_value=wrapped), \
             patch("app.services.task_worker._run_api_task") as mock_run:
            _process_api_tasks()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert call_args[0] == older.id, "Should pick the older task first"

    def test_semaphore_released_after_error(self, db_session):
        """Semaphore should be released even on error, so next polls can proceed."""
        from app.services.task_worker import _process_api_tasks, _semaphore_api

        initial = _semaphore_api._value

        # Force SessionLocal to raise an exception to test semaphore release
        with patch("app.core.db.SessionLocal", side_effect=RuntimeError("boom")):
            try:
                _process_api_tasks()
            except RuntimeError:
                pass

        assert _semaphore_api._value == initial, "Semaphore should be released after error"

    def test_semaphore_limits_concurrency(self, db_session):
        """When semaphore is exhausted, poll should return early without DB access."""
        from app.services.task_worker import _process_api_tasks, _semaphore_api

        # Exhaust the semaphore
        acquired = 0
        while _semaphore_api.acquire(blocking=False):
            acquired += 1

        try:
            with patch("app.core.db.SessionLocal") as mock_session_factory, \
                 patch("app.services.task_worker._run_api_task"):
                _process_api_tasks()
                # Should return immediately without creating a session
                mock_session_factory.assert_not_called()
        finally:
            for _ in range(acquired):
                _semaphore_api.release()


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
    def test_calls_all_three_processors(self):
        from app.services import task_worker

        with patch.object(task_worker, "_process_api_tasks") as mock_api, \
             patch.object(task_worker, "_process_ui_runs") as mock_ui, \
             patch("app.services.lanhu_evidence.worker.poll_and_execute_evidence_jobs") as mock_evidence:
            task_worker.poll_and_execute()
            mock_api.assert_called_once()
            mock_ui.assert_called_once()
            mock_evidence.assert_called_once()
