from __future__ import annotations

import pytest

from app.models.environment import Environment
from app.models.ui_test import UiTestJob, UiTestRun
from app.services import ui_test_service


def _job(db_session, *, environment_project_id: int = 1):
    environment = Environment(
        project_id=environment_project_id,
        name="Batch 60 production",
        env_type="prod",
        base_url="https://production.example.invalid",
        is_production=True,
    )
    db_session.add(environment)
    db_session.flush()
    job = UiTestJob(
        project_id=1,
        name="Production read-only smoke",
        test_spec="specs/production-smoke.spec.ts",
        environment_id=environment.id,
        creator_id=1,
    )
    db_session.add(job)
    db_session.commit()
    return job


def test_production_ui_run_requires_dedicated_permission(db_session):
    job = _job(db_session)

    with pytest.raises(PermissionError, match="uitest:trigger_prod"):
        ui_test_service.trigger_job(
            db_session,
            job.id,
            1,
            confirm_prod=True,
            has_trigger_prod=False,
        )

    assert db_session.query(UiTestRun).count() == 0
    assert job.status == "idle"


def test_production_ui_run_requires_explicit_confirmation(db_session):
    job = _job(db_session)

    with pytest.raises(ValueError, match="confirm_prod=true"):
        ui_test_service.trigger_job(
            db_session,
            job.id,
            1,
            confirm_prod=False,
            has_trigger_prod=True,
        )

    assert db_session.query(UiTestRun).count() == 0
    assert job.status == "idle"


def test_production_ui_run_queues_only_after_both_guards(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    job = _job(db_session)
    monkeypatch.setattr(
        "app.services.playwright_executor._check_playwright_installed",
        lambda: (False, "controlled test dependency state"),
    )

    result = ui_test_service.trigger_job(
        db_session,
        job.id,
        1,
        confirm_prod=True,
        has_trigger_prod=True,
    )

    assert result["status"] == "failed"
    assert result["base_url"] == "https://production.example.invalid"
    assert db_session.query(UiTestRun).count() == 1


def test_ui_run_rejects_cross_project_environment(db_session):
    job = _job(db_session, environment_project_id=2)

    with pytest.raises(ValueError, match="不属于当前项目"):
        ui_test_service.trigger_job(
            db_session,
            job.id,
            1,
            confirm_prod=True,
            has_trigger_prod=True,
        )

    assert db_session.query(UiTestRun).count() == 0


def test_trigger_endpoint_requires_and_forwards_production_confirmation(
    client,
    auth_headers,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    job = _job(db_session)
    monkeypatch.setattr(
        "app.services.playwright_executor._check_playwright_installed",
        lambda: (False, "controlled test dependency state"),
    )

    denied = client.post(f"/api/v1/ui-tests/{job.id}/trigger", headers=auth_headers)

    assert denied.status_code == 400
    assert "confirm_prod=true" in denied.json()["detail"]
    assert db_session.query(UiTestRun).count() == 0

    accepted = client.post(
        f"/api/v1/ui-tests/{job.id}/trigger",
        headers=auth_headers,
        json={"confirm_prod": True},
    )

    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "failed"
    assert db_session.query(UiTestRun).count() == 1
