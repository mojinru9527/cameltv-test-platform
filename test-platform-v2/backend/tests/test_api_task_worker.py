"""Legacy API task read-only contract after PR-09.

The legacy executor file is deleted. Historical task rows remain readable, and
all mutation routes must fail closed without touching them.
"""
from __future__ import annotations


def test_legacy_task_mutations_return_gone_without_writes(
    client, auth_headers, db_session
) -> None:
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
    from app.models.test_case import TestCase

    case = TestCase(
        project_id=1,
        title="Readonly Legacy Case",
        case_type="api",
        api_method="GET",
        api_endpoint="https://httpbin.org/get",
        api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
    )
    db_session.add(case)
    db_session.commit()
    task = ApiExecutionTask(
        project_id=1,
        task_id="T-READONLY",
        name="Readonly Legacy Task",
        total=1,
        status="pending",
    )
    db_session.add(task)
    db_session.flush()
    db_session.add(
        ApiExecutionTaskItem(task_id=task.id, case_id=case.id, status="failed")
    )
    db_session.commit()

    before_counts = (
        db_session.query(ApiExecutionTask).count(),
        db_session.query(ApiExecutionTaskItem).count(),
    )
    mutations = (
        ("post", f"/api/v1/apitest/tasks/{task.id}/cancel"),
        ("post", f"/api/v1/apitest/tasks/{task.id}/retry-failed"),
        ("delete", f"/api/v1/apitest/tasks/{task.id}"),
    )
    for method, url in mutations:
        response = getattr(client, method)(url, headers=auth_headers)
        assert response.status_code == 410
        assert "canonical ExecutionRun" in response.json()["detail"]

    db_session.expire_all()
    assert (
        db_session.query(ApiExecutionTask).count(),
        db_session.query(ApiExecutionTaskItem).count(),
    ) == before_counts
    refreshed = db_session.get(ApiExecutionTask, task.id)
    assert refreshed is not None
    assert refreshed.status == "pending"
    assert refreshed.cancel_requested is False


def test_legacy_task_mutations_preserve_project_isolation(
    client, auth_headers, db_session
) -> None:
    from app.models.api_asset import ApiExecutionTask

    task = ApiExecutionTask(
        project_id=999,
        task_id="T-FOREIGN-READONLY",
        name="Foreign Readonly Task",
        total=1,
        status="pending",
    )
    db_session.add(task)
    db_session.commit()

    for method, url in (
        ("post", f"/api/v1/apitest/tasks/{task.id}/cancel"),
        ("post", f"/api/v1/apitest/tasks/{task.id}/retry-failed"),
        ("delete", f"/api/v1/apitest/tasks/{task.id}"),
    ):
        response = getattr(client, method)(url, headers=auth_headers)
        assert response.status_code == 404
