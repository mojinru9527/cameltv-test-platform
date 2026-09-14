"""Permission boundary tests for user-supplied Playwright execution."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.deps import CurrentUser, get_current_user
from app.main import app
from app.schemas.playground import ExecuteResponse


def _client_with_permissions(db_session, user, permissions: list[str]) -> TestClient:
    import app.core.db as db_module

    def _current_user():
        return CurrentUser(
            user=user,
            permissions=permissions,
            project_id=1,
            system_permissions=["*"],
        )

    def _db():
        yield db_session

    app.dependency_overrides[db_module.get_db] = _db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def test_playground_execute_requires_code_execute_permission(db_session, admin_user):
    previous = app.dependency_overrides.get(get_current_user)
    test_client = _client_with_permissions(db_session, admin_user, ["uitest:trigger"])
    try:
        response = test_client.post(
            "/api/v1/playground/execute",
            headers={"X-Project-Id": "1"},
            json={"spec_code": "test('x', async () => {})"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous


def test_playground_execute_only_invokes_runner_with_code_permission(
    db_session, admin_user, monkeypatch
):
    previous = app.dependency_overrides.get(get_current_user)
    test_client = _client_with_permissions(db_session, admin_user, ["uitest:code_execute"])
    observed: list[str] = []

    def _execute(req):
        observed.append(req.spec_code)
        return ExecuteResponse(passed=True, stdout="ok")

    monkeypatch.setattr("app.api.v1.playground.execute_spec", _execute)
    try:
        response = test_client.post(
            "/api/v1/playground/execute",
            headers={"X-Project-Id": "1"},
            json={"spec_code": "test('x', async () => {})"},
        )
        assert response.status_code == 200
        assert observed == ["test('x', async () => {})"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous
