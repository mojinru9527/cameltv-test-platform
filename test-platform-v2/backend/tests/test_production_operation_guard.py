"""Batch 61 production-operation guard contract tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.exceptions import APIException
from app.models.audit import AuditLog
from app.models.api_asset import ApiExecutionTask
from app.models.environment import Environment
from app.models.integration import IntegrationConfig
from app.models.release_bundle import ReleaseBundle
from app.models.sync_log import SyncLog
from app.services.production_operation_guard import (
    ProductionOperation,
    require_allowed_operation,
)


def _environment(db_session, *, project_id: int = 1, production: bool = True) -> Environment:
    environment = Environment(
        project_id=project_id,
        name="Batch 61 target",
        env_type="prod" if production else "test",
        is_production=production,
        base_url="https://target.example.invalid",
    )
    db_session.add(environment)
    db_session.commit()
    return environment


def _operation(environment_id: int | None, **overrides) -> ProductionOperation:
    values = {
        "action": "Trigger release regression",
        "project_id": 1,
        "environment_id": environment_id,
        "permission": "uitest:trigger_prod",
        "confirmed": True,
    }
    values.update(overrides)
    return ProductionOperation(**values)


@pytest.mark.parametrize(
    ("operation", "expected_code"),
    [
        (_operation(None), 400),
        (_operation(999_999), 404),
    ],
)
def test_missing_or_unknown_environment_fails_closed_without_audit(
    db_session, operation, expected_code
):
    with pytest.raises(APIException) as exc_info:
        require_allowed_operation(db_session, operation, {"*"})

    assert exc_info.value.code == expected_code
    assert db_session.query(AuditLog).count() == 0


def test_environment_from_another_project_fails_closed_without_audit(db_session):
    environment = _environment(db_session, project_id=2)

    with pytest.raises(APIException) as exc_info:
        require_allowed_operation(db_session, _operation(environment.id), {"*"})

    assert exc_info.value.code == 404
    assert db_session.query(AuditLog).count() == 0


@pytest.mark.parametrize(
    ("permissions", "confirmed", "expected_code"),
    [
        ({"uitest:trigger"}, True, 403),
        ({"uitest:trigger_prod"}, False, 400),
    ],
)
def test_production_requires_dedicated_permission_and_confirmation(
    db_session, permissions, confirmed, expected_code
):
    environment = _environment(db_session)

    with pytest.raises(APIException) as exc_info:
        require_allowed_operation(
            db_session,
            _operation(environment.id, confirmed=confirmed),
            permissions,
        )

    assert exc_info.value.code == expected_code
    assert db_session.query(AuditLog).count() == 0


def test_authorized_production_operation_writes_human_readable_audit(db_session):
    environment = _environment(db_session)

    resolved = require_allowed_operation(
        db_session,
        _operation(environment.id),
        {"uitest:trigger_prod"},
    )

    assert resolved.id == environment.id
    audit = db_session.query(AuditLog).one()
    assert audit.action == "production_operation:allowed"
    assert "Trigger release regression" in audit.detail
    assert "Batch 61 target" in audit.target
    assert "https://target.example.invalid" in audit.target


def test_non_production_target_does_not_require_production_permission(db_session):
    environment = _environment(db_session, production=False)

    resolved = require_allowed_operation(
        db_session,
        _operation(environment.id, confirmed=False),
        set(),
    )

    assert resolved.id == environment.id
    assert db_session.query(AuditLog).count() == 1


def test_audit_failure_blocks_operation(db_session):
    environment = _environment(db_session)

    with patch(
        "app.services.production_operation_guard.write_audit",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError, match="audit unavailable"):
            require_allowed_operation(
                db_session,
                _operation(environment.id),
                {"uitest:trigger_prod"},
            )


def test_quick_execute_rejects_unconfirmed_production_before_network(
    client, auth_headers, db_session
):
    environment = _environment(db_session)
    audit_before = db_session.query(AuditLog).count()

    with patch("app.api.v1.apitest_tasks.quick_execute") as execute:
        response = client.post(
            "/api/v1/apitest/api-execute",
            headers=auth_headers,
            json={
                "method": "POST",
                "url": "/write",
                "environment_id": environment.id,
                "confirm_prod": False,
            },
        )

    assert response.status_code == 400
    assert "confirm_prod=true" in response.json()["msg"]
    execute.assert_not_called()
    assert db_session.query(AuditLog).count() == audit_before


def test_single_case_rejects_unconfirmed_production_before_execution(
    client, auth_headers, db_session
):
    from app.models.test_case import TestCase

    environment = _environment(db_session)
    case = TestCase(
        project_id=1,
        title="Guarded write case",
        case_type="api",
        api_method="POST",
        api_endpoint="/write",
    )
    db_session.add(case)
    db_session.commit()
    audit_before = db_session.query(AuditLog).count()

    with patch("app.api.v1.test_case_crud.execute_api_case") as execute:
        response = client.post(
            f"/api/v1/test-cases/{case.id}/execute",
            headers=auth_headers,
            json={"environment_id": environment.id, "confirm_prod": False},
        )

    assert response.status_code == 200
    assert response.json()["code"] == 400
    execute.assert_not_called()
    assert db_session.query(AuditLog).count() == audit_before


def test_batch_task_rejects_unconfirmed_production_before_rows(
    client, auth_headers, db_session
):
    from app.models.test_case import TestCase

    environment = _environment(db_session)
    case = TestCase(
        project_id=1,
        title="Guarded batch write",
        case_type="api",
        api_method="DELETE",
        api_endpoint="/write/1",
    )
    db_session.add(case)
    db_session.commit()
    audit_before = db_session.query(AuditLog).count()

    response = client.post(
        "/api/v1/apitest/tasks",
        headers=auth_headers,
        json={
            "name": "Guarded production batch",
            "case_ids": [case.id],
            "environment_id": environment.id,
            "confirm_prod": False,
        },
    )

    assert response.status_code == 400
    assert "confirm_prod=true" in response.json()["detail"]
    assert db_session.query(ApiExecutionTask).count() == 0
    assert db_session.query(AuditLog).count() == audit_before


def test_release_regression_rejects_unconfirmed_production_before_jobs(
    client, auth_headers, db_session
):
    environment = _environment(db_session)
    bundle = ReleaseBundle(project_id=1, name="Batch 61", client_version="61")
    db_session.add(bundle)
    db_session.commit()
    audit_before = db_session.query(AuditLog).count()

    response = client.post(
        f"/api/v1/release-bundles/{bundle.id}/trigger-regression",
        headers=auth_headers,
        json={"environment_id": environment.id, "confirm_prod": False},
    )

    assert response.status_code == 400
    assert "confirm_prod=true" in response.json()["msg"]
    from app.models.ui_test import UiTestJob

    assert db_session.query(UiTestJob).count() == 0
    assert db_session.query(AuditLog).count() == audit_before


def test_integration_sync_rejects_unconfirmed_production_before_sync_logs(
    client, auth_headers, db_session
):
    environment = _environment(db_session)
    integration = IntegrationConfig(
        project_id=1,
        name="Guarded Jira",
        provider_type="jira",
        base_url="https://jira.example.invalid",
        auth_json="encrypted",
        sync_direction="bidirectional",
    )
    db_session.add(integration)
    db_session.commit()
    audit_before = db_session.query(AuditLog).count()

    response = client.post(
        f"/api/v1/integrations/{integration.id}/sync-now",
        headers=auth_headers,
        params={"environment_id": environment.id, "confirm_prod": False},
    )

    assert response.status_code == 400
    assert "confirm_prod=true" in response.json()["msg"]
    assert db_session.query(SyncLog).count() == 0
    assert db_session.query(AuditLog).count() == audit_before


def test_quick_execute_allows_project_owned_test_environment_and_audits(
    client, auth_headers, db_session
):
    environment = _environment(db_session, production=False)
    audit_before = db_session.query(AuditLog).count()

    with patch(
        "app.api.v1.apitest_tasks.quick_execute",
        return_value={"status": "ok", "status_code": 200, "all_pass": True},
    ) as execute:
        response = client.post(
            "/api/v1/apitest/api-execute",
            headers=auth_headers,
            json={
                "method": "GET",
                "url": "/health",
                "assertions": '[{"type":"status_code","expected":200}]',
                "environment_id": environment.id,
            },
        )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    execute.assert_called_once()
    audit = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert db_session.query(AuditLog).count() == audit_before + 1
    assert audit.action == "production_operation:allowed"
    assert "Batch 61 target" in audit.target


def test_release_regression_allows_test_environment_and_records_target(
    client, auth_headers, db_session
):
    environment = _environment(db_session, production=False)
    bundle = ReleaseBundle(project_id=1, name="Batch 61", client_version="61")
    db_session.add(bundle)
    db_session.commit()
    audit_before = db_session.query(AuditLog).count()

    response = client.post(
        f"/api/v1/release-bundles/{bundle.id}/trigger-regression",
        headers=auth_headers,
        json={"environment_id": environment.id, "confirm_prod": False},
    )

    assert response.status_code == 200
    assert response.json()["data"]["triggered"] == 0
    assert db_session.query(AuditLog).count() == audit_before + 1
