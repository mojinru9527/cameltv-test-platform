"""Tests for UI artifact isolation — verify artifacts only come from run directory."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


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

        # Create a shared test-results file (must never enter the run directory)
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
        assert not (run_storage_dir / str(run.id) / "shared_screenshot.png").exists()

        # Cleanup
        spec_path.unlink(missing_ok=True)


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

    def test_download_returns_same_project_artifact(
        self, client, auth_headers, db_session, ui_job_factory, ui_run_factory, tmp_path,
    ):
        """The project guard must preserve valid downloads from the current project."""
        job = ui_job_factory(project_id=1)
        artifact_dir = tmp_path / "ui-runs" / "current"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "report.json").write_text('{"ok": true}', encoding="utf-8")
        run = ui_run_factory(
            job_id=job.id,
            status="done",
            artifact_dir=str(artifact_dir),
        )

        response = client.get(
            f"/api/v1/ui-tests/runs/{run.id}/artifacts/report.json",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    @pytest.mark.parametrize("endpoint_suffix", ["artifacts", "artifacts/report.json"])
    def test_artifact_endpoints_hide_runs_from_other_projects(
        self,
        endpoint_suffix,
        client,
        auth_headers,
        db_session,
        ui_job_factory,
        ui_run_factory,
        tmp_path,
    ):
        """A run must be scoped through run -> job -> current project for list and download."""
        other_job = ui_job_factory(project_id=999)
        artifact_dir = tmp_path / "ui-runs" / "foreign"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "report.json").write_text('{"secret": true}', encoding="utf-8")
        other_run = ui_run_factory(
            job_id=other_job.id,
            status="done",
            artifact_dir=str(artifact_dir),
        )

        response = client.get(
            f"/api/v1/ui-tests/runs/{other_run.id}/{endpoint_suffix}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_download_rejects_prefix_sibling_directory(
        self, db_session, ui_job_factory, ui_run_factory, tmp_path,
    ):
        """`.../1` must not authorize `.../10` merely because their strings share a prefix."""
        from app.api.v1.ui_test import download_artifact

        job = ui_job_factory(project_id=1)
        artifact_dir = tmp_path / "ui-runs" / "1"
        sibling_dir = tmp_path / "ui-runs" / "10"
        artifact_dir.mkdir(parents=True)
        sibling_dir.mkdir(parents=True)
        (sibling_dir / "secret.txt").write_text("foreign artifact", encoding="utf-8")
        run = ui_run_factory(
            job_id=job.id,
            status="done",
            artifact_dir=str(artifact_dir),
        )

        with pytest.raises(HTTPException) as exc_info:
            download_artifact(
                run_id=run.id,
                filename="../10/secret.txt",
                current=SimpleNamespace(project_id=1),
                db=db_session,
            )

        assert exc_info.value.status_code == 403
