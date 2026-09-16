"""PR-09 contract: plan jobs are historical rows, not an executable queue."""
from __future__ import annotations

import importlib.util
import json


def test_plan_execution_queue_executor_is_deleted() -> None:
    assert importlib.util.find_spec("app.services.plan_execution_queue") is None


def test_plan_execution_jobs_endpoint_returns_history_without_writes(
    db_session, client, auth_headers
) -> None:
    from app.models.plan_execution_job import PlanExecutionJob

    row = PlanExecutionJob(
        project_id=1,
        plan_id=42,
        creator_id=7,
        status="completed",
        request_json=json.dumps({"plan_id": 42}),
        result_json=json.dumps({"total": 1, "passed": 1}),
    )
    db_session.add(row)
    db_session.commit()

    response = client.get(
        "/api/v1/test-plans/42/execution-jobs", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == row.id
    assert response.json()["data"][0]["result"] == {"total": 1, "passed": 1}

    db_session.refresh(row)
    assert row.status == "completed"
    assert row.locked_by == ""
