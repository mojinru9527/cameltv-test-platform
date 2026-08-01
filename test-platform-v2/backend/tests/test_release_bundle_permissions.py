"""Release-bundle authorization and response-contract regressions."""
from __future__ import annotations

from app.core.deps import CurrentUser, get_current_user
from app.main import app
from app.models.project import Project, ProjectMember
from app.models.release_bundle import ReleaseBundle
from app.models.user import User


def test_regression_scope_requires_knowledge_view(client, db_session) -> None:
    db_session.add(Project(id=1, code="RELEASE-TEST", name="Release Test Project"))
    viewer = User(
        username="release_bundle_limited",
        password="unused",
        nickname="Limited viewer",
        email="release-bundle-limited@test.local",
        status=1,
    )
    db_session.add(viewer)
    db_session.flush()
    db_session.add(ProjectMember(project_id=1, user_id=viewer.id, role_id=1))
    bundle = ReleaseBundle(project_id=1, name="Permission regression", client_version="60")
    db_session.add(bundle)
    db_session.commit()

    def _limited_user() -> CurrentUser:
        return CurrentUser(
            user=viewer,
            permissions=["testcase:list"],
            project_id=1,
            system_permissions=[],
        )

    app.dependency_overrides[get_current_user] = _limited_user
    try:
        response = client.get(f"/api/v1/release-bundles/{bundle.id}/regression-scope")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["msg"] == "缺少权限：knowledge:view"


def test_empty_regression_scope_matches_frontend_contract(
    client,
    auth_headers,
    db_session,
) -> None:
    bundle = ReleaseBundle(
        project_id=1,
        name="Empty regression scope",
        client_version="60.0.0",
    )
    db_session.add(bundle)
    db_session.commit()

    response = client.get(
        f"/api/v1/release-bundles/{bundle.id}/regression-scope",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "bundle_id": bundle.id,
        "bundle_name": "Empty regression scope",
        "client_version": "60.0.0",
        "changed_modules": [],
        "regression_summary": [],
        "total_regression_cases": 0,
    }
