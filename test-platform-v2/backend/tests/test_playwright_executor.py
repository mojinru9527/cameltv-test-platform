"""Tests for Playwright executor — Popen process management, cancel, timeout, PID recording."""
from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ui_job_factory(db_session):
    """Factory to create a UiTestJob."""
    from app.models.ui_test import UiTestJob

    def _create(**kwargs):
        defaults = {
            "project_id": 1,
            "name": "Test Job",
            "test_spec": "specs/example.spec.ts",
            "browser": "chromium",
            "status": "idle",
            "creator_id": 1,
        }
        defaults.update(kwargs)
        job = UiTestJob(**defaults)
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _create


@pytest.fixture
def ui_run_factory(db_session):
    """Factory to create a UiTestRun."""
    from app.models.ui_test import UiTestRun

    def _create(**kwargs):
        defaults = {
            "job_id": 1,
            "status": "pending",
            "base_url": "https://example.com",
            "result": json.dumps({}),
        }
        defaults.update(kwargs)
        run = UiTestRun(**defaults)
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    return _create


class TestPlaywrightExecutorModelFields:
    """Verify new fields exist on UiTestRun model."""

    def test_run_has_process_id_field(self, db_session, ui_run_factory):
        """UiTestRun should have process_id field (nullable int)."""
        run = ui_run_factory()
        assert hasattr(run, "process_id")
        assert run.process_id is None

        run.process_id = 12345
        db_session.commit()
        db_session.refresh(run)
        assert run.process_id == 12345

    def test_run_has_cancel_requested_field(self, db_session, ui_run_factory):
        """UiTestRun should have cancel_requested field (bool, default False)."""
        run = ui_run_factory()
        assert hasattr(run, "cancel_requested")
        assert run.cancel_requested is False

        run.cancel_requested = True
        db_session.commit()
        db_session.refresh(run)
        assert run.cancel_requested is True

    def test_run_has_artifact_fields(self, db_session, ui_run_factory):
        """UiTestRun should have artifact_dir, report_json_path, html_report_path."""
        run = ui_run_factory()
        run.artifact_dir = "storage/ui-runs/123"
        run.report_json_path = "storage/ui-runs/123/report.json"
        run.html_report_path = "storage/ui-runs/123/index.html"
        db_session.commit()
        db_session.refresh(run)
        assert run.artifact_dir == "storage/ui-runs/123"
        assert run.report_json_path == "storage/ui-runs/123/report.json"
        assert run.html_report_path == "storage/ui-runs/123/index.html"

    def test_run_has_stdout_stderr_fields(self, db_session, ui_run_factory):
        """UiTestRun should have stdout and stderr text fields."""
        run = ui_run_factory()
        run.stdout = "Test passed"
        run.stderr = "Warning: deprecated API"
        db_session.commit()
        db_session.refresh(run)
        assert run.stdout == "Test passed"
        assert run.stderr == "Warning: deprecated API"


class TestPlaywrightExecutorPopen:
    """Verify subprocess.Popen is used instead of subprocess.run."""

    def test_executor_records_pid(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """Executor should record process_id from Popen.pid."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        # Create the spec file so validation passes
        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        # Mock subprocess.Popen to return a fake process
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0  # Process done immediately
        mock_proc.communicate.return_value = ('{"suites":[]}', "")
        mock_proc.returncode = 0

        mock_popen = MagicMock(return_value=mock_proc)

        with patch("subprocess.Popen", mock_popen):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                from app.services.playwright_executor import run_playwright_test
                run_playwright_test(db_session, run.id, job.id, job.project_id)

        db_session.refresh(run)
        # PID should have been recorded
        assert run.process_id == 99999

        # Cleanup
        spec_path.unlink(missing_ok=True)

    def test_executor_sets_artifact_dir(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """Executor should set artifact_dir to storage/ui-runs/{run_id}."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = ('{"suites":[]}', "")
        mock_proc.returncode = 0

        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                from app.services.playwright_executor import run_playwright_test
                run_playwright_test(db_session, run.id, job.id, job.project_id)

        db_session.refresh(run)
        assert run.artifact_dir is not None
        assert run.artifact_dir != ""
        assert f"ui-runs/{run.id}" in run.artifact_dir.replace("\\", "/")

        # Cleanup
        spec_path.unlink(missing_ok=True)

    def test_executor_sets_report_json_path(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """Executor should set report_json_path to artifact_dir/report.json."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = ('{"suites":[]}', "")
        mock_proc.returncode = 0

        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                from app.services.playwright_executor import run_playwright_test
                run_playwright_test(db_session, run.id, job.id, job.project_id)

        db_session.refresh(run)
        assert run.report_json_path is not None
        assert run.report_json_path.endswith("report.json")

        # Cleanup
        spec_path.unlink(missing_ok=True)


class TestPlaywrightExecutorCancel:
    """Verify cancel_requested flag triggers process kill."""

    def test_cancel_during_poll_loop_kills_process(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """When cancel_requested is set, executor should kill the process."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        # Public execution now owns the pending -> running CAS transition.
        run = ui_run_factory(job_id=job.id, status="pending", cancel_requested=False)

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        # First poll: still running, then cancel is detected
        mock_proc.poll.side_effect = [None, None]  # Two polls, then we simulate cancel
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = None

        # We'll set cancel_requested via a side effect on poll
        call_count = [0]

        def poll_side_effect():
            call_count[0] += 1
            if call_count[0] >= 2:
                # Simulate cancel being set between polls
                run.cancel_requested = True
                db_session.commit()
                return None  # Still running, but cancel flag is now set
            return None  # First poll: still running

        mock_proc.poll.side_effect = poll_side_effect

        # Override time.sleep to not actually wait
        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                with patch("app.services.playwright_executor.time.sleep", return_value=None):
                    from app.services.playwright_executor import run_playwright_test
                    result = run_playwright_test(db_session, run.id, job.id, job.project_id)

        # Process should have been killed
        mock_proc.kill.assert_called()
        assert result.get("status") == "cancelled"

        # Cleanup
        spec_path.unlink(missing_ok=True)

    def test_cancel_pending_run_directly(self, db_session, ui_job_factory, ui_run_factory):
        """Cancel API should handle pending runs by setting status directly."""
        job = ui_job_factory()
        run = ui_run_factory(job_id=job.id, status="pending")

        # Simulate what the cancel endpoint does for pending runs
        run.cancel_requested = True
        run.status = "cancelled"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = "用户手动取消"
        db_session.commit()
        db_session.refresh(run)

        assert run.status == "cancelled"
        assert run.cancel_requested is True
        assert run.error_message == "用户手动取消"


class TestPlaywrightExecutorTimeout:
    """Verify timeout handling kills the process."""

    def test_timeout_kills_process(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """When timeout is exceeded, executor should kill the process and mark fail."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = None  # Always running
        mock_proc.communicate.return_value = ("partial output", "")
        mock_proc.returncode = None

        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                with patch("app.services.playwright_executor.time.sleep", return_value=None):
                    # Force timeout by using a very short timeout
                    with patch("app.services.playwright_executor.DEFAULT_TIMEOUT", 0):
                        from app.services.playwright_executor import run_playwright_test
                        result = run_playwright_test(db_session, run.id, job.id, job.project_id)

        db_session.refresh(run)
        # Process should have been killed
        mock_proc.kill.assert_called()
        assert run.status == "fail"
        assert "超时" in (run.error_message or "")

        # Cleanup
        spec_path.unlink(missing_ok=True)


class TestPlaywrightExecutorStdoutStderr:
    """Verify stdout/stderr are captured to the model."""

    def test_executor_captures_stdout(self, db_session, ui_job_factory, ui_run_factory, monkeypatch):
        """Executor should store process stdout in the run model."""
        job = ui_job_factory(test_spec="specs/example.spec.ts")

        from app.services.playwright_executor import PLAYWRIGHT_DIR
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0  # Done immediately
        mock_proc.communicate.return_value = ('{"suites":[]}', "some stderr output")
        mock_proc.returncode = 0

        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                from app.services.playwright_executor import run_playwright_test
                run_playwright_test(db_session, run.id, job.id, job.project_id)

        db_session.refresh(run)
        assert run.stdout is not None
        assert run.stderr is not None

        # Cleanup
        spec_path.unlink(missing_ok=True)


class TestPlaywrightJsonReportFile:
    """The JSON reporter may write only to PLAYWRIGHT_JSON_OUTPUT_NAME."""

    @staticmethod
    def _report(*statuses: str) -> dict:
        return {
            "suites": [{
                "specs": [{
                    "tests": [{
                        "results": [{"status": status, "duration": 100}],
                    } for status in statuses],
                }],
            }],
        }

    def test_empty_stdout_reads_success_report_from_current_run_dir(
        self, db_session, ui_job_factory, ui_run_factory, monkeypatch, tmp_path,
    ):
        from app.services import playwright_executor

        playwright_dir = tmp_path / "playwright"
        storage_dir = tmp_path / "ui-runs"
        spec_path = playwright_dir / "specs" / "report-file.spec.ts"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        job = ui_job_factory(test_spec="specs/report-file.spec.ts")
        run = ui_run_factory(job_id=job.id)
        artifact_dir = storage_dir / str(run.id)
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "report.json").write_text(
            json.dumps(self._report("passed")), encoding="utf-8",
        )
        # A conflicting shared report must never influence this run.
        (playwright_dir / "report.json").write_text(
            json.dumps(self._report(*(["failed"] * 5))), encoding="utf-8",
        )

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0

        monkeypatch.setattr(playwright_executor, "PLAYWRIGHT_DIR", playwright_dir)
        monkeypatch.setattr(playwright_executor, "STORAGE_DIR", storage_dir)
        monkeypatch.setattr(playwright_executor, "_resolve_cmd", lambda _: "npx")
        monkeypatch.setattr(playwright_executor.subprocess, "Popen", MagicMock(return_value=mock_proc))

        result = playwright_executor.run_playwright_test(
            db_session, run.id, job.id, job.project_id,
        )

        assert result["status"] == "done"
        assert result["result"]["total"] == 1
        assert result["result"]["pass_"] == 1
        assert result["result"]["fail"] == 0

    def test_empty_stdout_reads_failed_report_before_treating_exit_one_as_executor_error(
        self, db_session, ui_job_factory, ui_run_factory, monkeypatch, tmp_path,
    ):
        from app.services import playwright_executor

        playwright_dir = tmp_path / "playwright"
        storage_dir = tmp_path / "ui-runs"
        spec_path = playwright_dir / "specs" / "report-file.spec.ts"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        job = ui_job_factory(test_spec="specs/report-file.spec.ts")
        run = ui_run_factory(job_id=job.id)
        artifact_dir = storage_dir / str(run.id)
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "report.json").write_text(
            json.dumps(self._report("passed", "failed")), encoding="utf-8",
        )
        # If the executor accidentally reads outside artifact_dir, totals differ.
        (playwright_dir / "report.json").write_text(
            json.dumps(self._report(*(["passed"] * 7))), encoding="utf-8",
        )

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 1
        mock_proc.communicate.return_value = ("", "assertion failed")
        mock_proc.returncode = 1

        monkeypatch.setattr(playwright_executor, "PLAYWRIGHT_DIR", playwright_dir)
        monkeypatch.setattr(playwright_executor, "STORAGE_DIR", storage_dir)
        monkeypatch.setattr(playwright_executor, "_resolve_cmd", lambda _: "npx")
        monkeypatch.setattr(playwright_executor.subprocess, "Popen", MagicMock(return_value=mock_proc))

        result = playwright_executor.run_playwright_test(
            db_session, run.id, job.id, job.project_id,
        )

        assert result["status"] == "fail"
        assert result["result"]["total"] == 2
        assert result["result"]["pass_"] == 1
        assert result["result"]["fail"] == 1
        assert result["error_message"] == ""


class TestPlaywrightExecutorHelperFunctions:
    """Test helper functions directly."""

    def test_collect_artifacts_only_from_specified_dir(self, tmp_path):
        """_collect_artifacts should only return files from the given directory."""
        from app.services.playwright_executor import _collect_artifacts

        # Create artifacts in a specific dir
        run_dir = tmp_path / "ui-runs" / "123"
        run_dir.mkdir(parents=True)
        (run_dir / "screenshot1.png").write_text("fake png")
        (run_dir / "video1.webm").write_text("fake video")
        (run_dir / "trace.zip").write_text("fake trace")

        # Create files in another directory (should NOT be collected)
        other_dir = tmp_path / "other"
        other_dir.mkdir(parents=True)
        (other_dir / "leak.png").write_text("should not appear")

        pngs = _collect_artifacts(run_dir, "*.png")
        assert len(pngs) == 1
        assert "screenshot1.png" in pngs[0]
        # Should NOT contain files from other_dir
        assert not any("leak" in p for p in pngs)

    def test_executor_uses_bounded_thread_semaphore(self):
        from app.services import playwright_executor

        assert playwright_executor._semaphore.__class__.__name__ == "BoundedSemaphore"

    def test_busy_semaphore_does_not_requeue_running_run(
        self, db_session, ui_job_factory, ui_run_factory, monkeypatch,
    ):
        from app.services import playwright_executor

        job = ui_job_factory()
        run = ui_run_factory(job_id=job.id, status="running")
        semaphore = MagicMock()
        semaphore.acquire.return_value = False
        monkeypatch.setattr(playwright_executor, "_semaphore", semaphore)
        popen = MagicMock()
        monkeypatch.setattr(playwright_executor.subprocess, "Popen", popen)

        result = playwright_executor.run_playwright_test(
            db_session, run.id, job.id, job.project_id,
        )

        db_session.refresh(run)
        assert result == {"status": "running", "run_id": run.id}
        assert run.status == "running"
        semaphore.acquire.assert_called_once_with(blocking=False)
        semaphore.release.assert_not_called()
        popen.assert_not_called()

    def test_busy_semaphore_leaves_unclaimed_run_pending(
        self, db_session, ui_job_factory, ui_run_factory, monkeypatch,
    ):
        from app.services import playwright_executor

        job = ui_job_factory()
        run = ui_run_factory(job_id=job.id, status="pending")
        semaphore = MagicMock()
        semaphore.acquire.return_value = False
        monkeypatch.setattr(playwright_executor, "_semaphore", semaphore)
        popen = MagicMock()
        monkeypatch.setattr(playwright_executor.subprocess, "Popen", popen)

        result = playwright_executor.run_playwright_test(
            db_session, run.id, job.id, job.project_id,
        )

        db_session.refresh(run)
        assert result == {"status": "pending", "run_id": run.id}
        assert run.status == "pending"
        semaphore.release.assert_not_called()
        popen.assert_not_called()

    def test_immediate_queue_and_periodic_worker_atomically_claim_run_once(
        self, monkeypatch, tmp_path,
    ):
        """Two independent consumers racing the same pending run execute it exactly once."""
        import app.models  # noqa: F401 - register all mapped tables
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.core.db import Base
        from app.models.ui_test import UiTestJob, UiTestRun
        from app.services import playwright_executor

        database_path = (tmp_path / "ui-claim.db").as_posix()
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(
            engine,
            tables=[UiTestJob.__table__, UiTestRun.__table__],
        )
        session_factory = sessionmaker(bind=engine)
        with session_factory() as setup_db:
            job = UiTestJob(
                project_id=1,
                name="CAS job",
                test_spec="specs/cas.spec.ts",
                browser="chromium",
                status="running",
                creator_id=1,
            )
            setup_db.add(job)
            setup_db.flush()
            run = UiTestRun(job_id=job.id, status="pending")
            setup_db.add(run)
            setup_db.commit()
            job_id = job.id
            run_id = run.id

        semaphore = threading.BoundedSemaphore(2)
        monkeypatch.setattr(playwright_executor, "_semaphore", semaphore)
        execution_calls: list[int] = []
        calls_lock = threading.Lock()

        def fake_execute(db, claimed_run_id, claimed_job_id, project_id):
            with calls_lock:
                execution_calls.append(claimed_run_id)
            time.sleep(0.1)
            return {"status": "done", "run_id": claimed_run_id}

        monkeypatch.setattr(playwright_executor, "_run_playwright_test", fake_execute)
        start = threading.Barrier(2)

        def consume():
            with session_factory() as consumer_db:
                start.wait(timeout=5)
                return playwright_executor.run_playwright_test(
                    consumer_db, run_id, job_id, 1,
                )

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = [future.result(timeout=5) for future in [
                    pool.submit(consume),
                    pool.submit(consume),
                ]]

            assert execution_calls == [run_id]
            assert sorted(result["status"] for result in results) == ["done", "running"]

            # Both the winning and losing consumers must release their slots.
            assert semaphore.acquire(blocking=False) is True
            assert semaphore.acquire(blocking=False) is True
            assert semaphore.acquire(blocking=False) is False
            semaphore.release()
            semaphore.release()
        finally:
            engine.dispose()

    def test_executor_does_not_copy_shared_test_results(
        self, db_session, ui_job_factory, ui_run_factory, monkeypatch, tmp_path,
    ):
        from app.services import playwright_executor

        playwright_dir = tmp_path / "playwright"
        storage_dir = tmp_path / "ui-runs"
        spec_path = playwright_dir / "specs" / "isolated.spec.ts"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text("// mock spec", encoding="utf-8")
        shared_dir = playwright_dir / "test-results"
        shared_dir.mkdir()
        (shared_dir / "foreign.png").write_bytes(b"foreign")

        job = ui_job_factory(test_spec="specs/isolated.spec.ts")
        run = ui_run_factory(job_id=job.id)
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = ('{"suites":[]}', "")
        mock_proc.returncode = 0

        monkeypatch.setattr(playwright_executor, "PLAYWRIGHT_DIR", playwright_dir)
        monkeypatch.setattr(playwright_executor, "STORAGE_DIR", storage_dir)
        monkeypatch.setattr(playwright_executor, "_resolve_cmd", lambda _: "npx")
        monkeypatch.setattr(playwright_executor.subprocess, "Popen", MagicMock(return_value=mock_proc))

        playwright_executor.run_playwright_test(db_session, run.id, job.id, job.project_id)

        run_dir = storage_dir / str(run.id)
        assert not (run_dir / "foreign.png").exists()
        assert not (run_dir / "test-results" / "foreign.png").exists()

    def test_resolve_cmd_finds_npx(self, monkeypatch):
        """_resolve_cmd should locate npx when available."""
        from app.services.playwright_executor import _resolve_cmd

        # Mock shutil.which to simulate npx present
        with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
            result = _resolve_cmd("npx")
            assert result == "/usr/bin/npx"

    def test_resolve_cmd_returns_none_when_missing(self, monkeypatch):
        """_resolve_cmd should return None when command not found."""
        from app.services.playwright_executor import _resolve_cmd

        with patch("app.services.playwright_executor.shutil.which", return_value=None):
            result = _resolve_cmd("nonexistent-cmd")
            assert result is None

    def test_list_available_specs(self, monkeypatch, tmp_path):
        """_list_available_specs should find .spec.js and .spec.ts files."""
        from app.services.playwright_executor import _list_available_specs

        # Create a temp playwright dir with spec files
        specs_dir = tmp_path / "playwright"
        specs_dir.mkdir(parents=True)
        (specs_dir / "test1.spec.ts").write_text("// test1")
        (specs_dir / "test2.spec.js").write_text("// test2")
        (specs_dir / "not-a-test.txt").write_text("// not a test")
        sub_dir = specs_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / "test3.spec.ts").write_text("// test3")

        with patch("app.services.playwright_executor.PLAYWRIGHT_DIR", specs_dir):
            specs = _list_available_specs()
            assert len(specs) == 3
            assert any("test1.spec.ts" in s for s in specs)
            assert any("test2.spec.js" in s for s in specs)
            assert any("sub/test3.spec.ts" in s for s in specs)
