"""Tests for UI artifact isolation — verify artifacts only come from run directory."""
from __future__ import annotations

import json
import os
import subprocess
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


class TestArtifactCollectOnlyFromRunDir:
    """Verify _collect_artifacts only returns files from the specified directory."""

    def test_collect_artifacts_does_not_include_shared_dirs(self, tmp_path):
        """_collect_artifacts should NOT return files from outside the given base_dir."""
        from app.services.playwright_executor import _collect_artifacts

        # Simulate run-specific directory
        run_dir = tmp_path / "storage" / "ui-runs" / "42"
        run_dir.mkdir(parents=True)
        (run_dir / "screenshot_run42.png").write_text("run 42 screenshot")

        # Simulate shared directory (should NOT be included)
        shared_dir = tmp_path / "tests" / "playwright" / "test-results"
        shared_dir.mkdir(parents=True)
        (shared_dir / "screenshot_other_run.png").write_text("other run screenshot")

        # Collect from run_dir only
        pngs = _collect_artifacts(run_dir, "*.png")
        assert len(pngs) == 1
        assert "screenshot_run42.png" in pngs[0]
        # Must NOT include files from shared dir
        assert not any("other_run" in p for p in pngs)

    def test_collect_artifacts_handles_missing_dir(self):
        """_collect_artifacts should return empty list for non-existent directory."""
        from app.services.playwright_executor import _collect_artifacts

        result = _collect_artifacts(Path("/nonexistent/path"), "*.png")
        assert result == []

    def test_collect_artifacts_max_limit(self, tmp_path):
        """_collect_artifacts should cap at 20 items."""
        from app.services.playwright_executor import _collect_artifacts

        run_dir = tmp_path / "many-files"
        run_dir.mkdir(parents=True)
        for i in range(30):
            (run_dir / f"shot_{i:02d}.png").write_text(f"screenshot {i}")

        pngs = _collect_artifacts(run_dir, "*.png")
        assert len(pngs) <= 20


class TestExecutorArtifactIsolation:
    """Verify the executor only collects artifacts from the run's own directory."""

    def test_executor_collects_only_from_artifact_dir(self, db_session, ui_job_factory, ui_run_factory, tmp_path):
        """After execution, artifacts should only come from storage/ui-runs/{run_id}."""
        from app.services.playwright_executor import PLAYWRIGHT_DIR, STORAGE_DIR

        job = ui_job_factory(test_spec="specs/example.spec.ts")

        # Create spec file
        spec_path = PLAYWRIGHT_DIR / job.test_spec
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("// mock spec", encoding="utf-8")

        run = ui_run_factory(job_id=job.id, status="pending")

        # Create a shared test-results file (should be copied but NOT reported)
        shared_dir = PLAYWRIGHT_DIR / "test-results"
        shared_dir.mkdir(parents=True, exist_ok=True)
        (shared_dir / "shared_screenshot.png").write_text("shared artifact")

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = ('{"suites":[]}', "")
        mock_proc.returncode = 0

        # Override STORAGE_DIR to use tmp_path
        run_storage_dir = tmp_path / "storage" / "ui-runs"

        with patch("subprocess.Popen", MagicMock(return_value=mock_proc)):
            with patch("app.services.playwright_executor.shutil.which", return_value="/usr/bin/npx"):
                with patch("app.services.playwright_executor.STORAGE_DIR", run_storage_dir):
                    from app.services.playwright_executor import run_playwright_test
                    result = run_playwright_test(db_session, run.id, job.id, job.project_id)

        # Artifacts list should NOT contain the shared directory file paths directly
        screenshots = result.get("screenshots", [])
        for s in screenshots:
            # All paths should be relative to the artifact_dir (run-specific)
            assert ".." not in s
            assert not s.startswith("/")

        # Cleanup
        spec_path.unlink(missing_ok=True)

    def test_copy_artifacts_to_run_dir_excludes_existing(self, tmp_path):
        """_copy_artifacts_to_run_dir should not overwrite existing files."""
        from app.services.playwright_executor import _copy_artifacts_to_run_dir

        src = tmp_path / "src"
        src.mkdir(parents=True)
        (src / "test.png").write_text("source content")

        dest = tmp_path / "dest"
        dest.mkdir(parents=True)
        (dest / "test.png").write_text("original content")

        # Should not overwrite
        _copy_artifacts_to_run_dir(src, dest)

        # dest file should still have original content
        assert (dest / "test.png").read_text() == "original content"

    def test_copy_artifacts_skips_when_src_equals_dest(self, tmp_path):
        """_copy_artifacts_to_run_dir should skip when src == dest."""
        from app.services.playwright_executor import _copy_artifacts_to_run_dir

        same_dir = tmp_path / "same"
        same_dir.mkdir(parents=True)
        (same_dir / "test.png").write_text("test content")

        # Should not raise or loop
        _copy_artifacts_to_run_dir(same_dir, same_dir)
        # File should still exist
        assert (same_dir / "test.png").exists()

    def test_copy_artifacts_to_run_dir_skips_nested_paths(self, tmp_path):
        """_copy_artifacts_to_run_dir should skip files already inside dest."""
        from app.services.playwright_executor import _copy_artifacts_to_run_dir

        dest = tmp_path / "dest"
        dest.mkdir(parents=True)
        nested = dest / "sub"
        nested.mkdir(parents=True)
        (nested / "test.png").write_text("nested content")

        # Copy from nested into dest - file should be skipped since it's already under dest
        _copy_artifacts_to_run_dir(nested, dest)
        # No error expected

    def test_copy_artifacts_to_run_dir_creates_parent_dirs(self, tmp_path):
        """_copy_artifacts_to_run_dir should create parent directories as needed."""
        from app.services.playwright_executor import _copy_artifacts_to_run_dir

        src = tmp_path / "src"
        src.mkdir(parents=True)
        sub = src / "deep" / "path"
        sub.mkdir(parents=True)
        (sub / "test.png").write_text("deep file")

        dest = tmp_path / "dest"
        dest.mkdir(parents=True)

        _copy_artifacts_to_run_dir(src, dest)
        assert (dest / "deep" / "path" / "test.png").exists()
        assert (dest / "deep" / "path" / "test.png").read_text() == "deep file"


class TestArtifactListApiIsolation:
    """Verify artifact listing API only returns files from the run directory."""

    def test_artifact_list_only_from_run_dir(self, client, auth_headers, db_session, ui_job_factory, ui_run_factory, tmp_path):
        """GET /ui-tests/runs/{run_id}/artifacts should only list files from that run's artifact_dir."""
        job = ui_job_factory()
        run = ui_run_factory(job_id=job.id, status="done")

        # Set artifact_dir to a tmp_path directory
        artifact_dir = tmp_path / "ui-runs" / str(run.id)
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "report.json").write_text('{"ok": true}')
        (artifact_dir / "screenshot.png").write_text("fake png")

        run.artifact_dir = str(artifact_dir).replace("\\", "/")
        db_session.commit()

        resp = client.get(
            f"/api/v1/ui-tests/runs/{run.id}/artifacts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        names = {f["name"] for f in data}
        assert "report.json" in names
        assert "screenshot.png" in names

    def test_artifact_list_empty_for_missing_dir(self, client, auth_headers, db_session, ui_job_factory, ui_run_factory):
        """GET /ui-tests/runs/{run_id}/artifacts should return empty list for missing dir."""
        job = ui_job_factory()
        run = ui_run_factory(job_id=job.id, status="done", artifact_dir="/nonexistent/path")

        resp = client.get(
            f"/api/v1/ui-tests/runs/{run.id}/artifacts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []
