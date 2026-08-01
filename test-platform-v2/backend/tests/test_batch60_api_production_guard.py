"""Batch 60 production guard coverage for API case and task entry points."""
from __future__ import annotations

from unittest.mock import patch

from app.models.api_asset import ApiExecutionTask
from app.models.environment import Environment
from app.models.test_case import TestCase


def test_single_api_case_forwards_superuser_production_permission(
    client, auth_headers, db_session
):
    case = TestCase(
        project_id=1,
        title="Batch 60 production write",
        case_type="api",
        api_method="POST",
        api_endpoint="https://example.invalid/write",
    )
    env = Environment(
        project_id=1,
        name="Batch 60 production",
        env_type="prod",
        is_production=True,
        base_url="https://example.invalid",
    )
    db_session.add_all([case, env])
    db_session.commit()

    with patch(
        "app.api.v1.test_case.execute_api_case",
        return_value={"status_code": 200, "all_pass": True},
    ) as execute:
        response = client.post(
            f"/api/v1/test-cases/{case.id}/execute",
            headers=auth_headers,
            json={"environment_id": env.id, "confirm_prod": True},
        )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert execute.call_args.kwargs["has_execute_prod"] is True


def test_api_task_rejects_environment_from_another_project(
    client, auth_headers, db_session
):
    case = TestCase(
        project_id=1,
        title="Batch 60 scoped case",
        case_type="api",
        api_method="GET",
        api_endpoint="https://example.invalid/read",
    )
    foreign_env = Environment(
        project_id=2,
        name="Foreign environment",
        env_type="test",
        base_url="https://example.invalid",
    )
    db_session.add_all([case, foreign_env])
    db_session.commit()

    response = client.post(
        "/api/v1/apitest/tasks",
        headers=auth_headers,
        json={
            "name": "Batch 60 foreign environment",
            "case_ids": [case.id],
            "environment_id": foreign_env.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "环境不存在或不属于当前项目"
    assert db_session.query(ApiExecutionTask).count() == 0
