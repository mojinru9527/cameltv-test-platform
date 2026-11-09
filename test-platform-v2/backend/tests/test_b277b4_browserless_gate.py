"""batch-277b-4 / P0-4：控制面无浏览器开关的门禁测试。"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.ui_test import UiTestJob, UiTestRun
from app.services import playwright_executor, ui_test_service, xhr_capture_service
from app.services.lanhu_evidence import screenshot_service

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = REPO_ROOT / "test-platform-v2" / "backend" / "Dockerfile"


def _mk_job(db) -> UiTestJob:
    job = UiTestJob(project_id=1, name="ui", test_spec="specs/x.spec.ts", browser="chromium")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_control_plane_browser_default_enabled():
    assert settings.control_plane_browser_enabled is True


def test_xhr_capture_returns_503_when_browser_disabled(monkeypatch):
    monkeypatch.setattr(settings, "control_plane_browser_enabled", False)
    with pytest.raises(APIException) as exc:
        xhr_capture_service.create_capture_task(pages=["https://example.test"], project_id=1)
    assert exc.value.code == 503
    assert "控制面浏览器已禁用" in exc.value.msg


def test_ui_trigger_local_mode_fails_when_browser_disabled(db_session, monkeypatch):
    monkeypatch.setattr(settings, "control_plane_browser_enabled", False)
    monkeypatch.setattr(settings, "uitest_execution_mode", "local")
    job = _mk_job(db_session)
    result = ui_test_service.trigger_job(db_session, job.id, 1)
    run = db_session.get(UiTestRun, result["id"])
    assert run.status == "failed"
    assert "控制面浏览器已禁用" in run.error_message


def test_playwright_executor_fails_run_when_browser_disabled(db_session, monkeypatch):
    monkeypatch.setattr(settings, "control_plane_browser_enabled", False)
    job = _mk_job(db_session)
    run = UiTestRun(job_id=job.id, status="pending", base_url="")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    playwright_executor.run_playwright_test(db_session, run.id, job.id, 1)
    db_session.refresh(run)
    assert run.status == "failed"
    assert "CONTROL_PLANE_BROWSER_ENABLED=false" in run.error_message


def test_lanhu_capture_returns_error_when_browser_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "control_plane_browser_enabled", False)
    result = asyncio.run(
        screenshot_service.capture_page_segments("https://example.test", tmp_path, "page-1")
    )
    assert result.error and "控制面浏览器已禁用" in result.error


def test_playground_execute_returns_503_when_browser_disabled(monkeypatch):
    from app.schemas.playground import ExecuteRequest
    from app.services import playground_service

    monkeypatch.setattr(settings, "control_plane_browser_enabled", False)
    req = ExecuteRequest(spec_code="test('x', async () => {});", base_url="https://example.test")
    with pytest.raises(APIException) as exc:
        playground_service.execute_spec(req)
    assert exc.value.code == 503


def test_dockerfile_no_longer_installs_browser():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "playwright install" not in text
    assert "CONTROL_PLANE_BROWSER_ENABLED=false" in text
    assert "UITEST_EXECUTION_MODE=node" in text
