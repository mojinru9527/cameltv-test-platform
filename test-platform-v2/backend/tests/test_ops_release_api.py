"""Operations API must consume the separate persisted release-control facts."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

from app.core.config import settings
from app.core.deps import CurrentUser, get_current_user
from app.main import app

RELEASE_CONTROL_SOURCE = Path(__file__).resolve().parents[3] / "deploy" / "release-control" / "src"
if str(RELEASE_CONTROL_SOURCE) not in sys.path:
    sys.path.insert(0, str(RELEASE_CONTROL_SOURCE))

from cameltv_release.state_machine import ReleaseControlService  # noqa: E402
from cameltv_release.store import ReleaseStore  # noqa: E402
from cameltv_release.contracts import ReleaseManifest  # noqa: E402


@pytest.fixture
def manifest() -> ReleaseManifest:
    return ReleaseManifest.model_validate(
        {
            "schema_version": "1.0",
            "release_id": "b62-test-20260802-0001",
            "git_sha": "1" * 40,
            "frontend": {
                "image": "registry.test.invalid/cameltv/frontend",
                "digest": "sha256:" + "a" * 64,
                "sbom_sha256": "b" * 64,
            },
            "backend": {
                "image": "registry.test.invalid/cameltv/backend",
                "digest": "sha256:" + "c" * 64,
                "sbom_sha256": "d" * 64,
                "openapi_sha256": "e" * 64,
            },
            "database": {
                "alembic_heads": ["batch62_release_core"],
                "target_revision": "batch62_release_core",
                "rollback_mode": "application-rollback-or-forward-fix",
            },
            "config_schema": "platform-runtime/v1",
            "secret_refs": ["secret://test/cameltv/platform@v1"],
            "qa_evidence": ["artifact://batch62/qa-report.json"],
        }
    )


def _configure_store(tmp_path, manifest) -> tuple[ReleaseStore, str]:
    database_path = tmp_path / "release-control.sqlite3"
    store = ReleaseStore(database_path)
    service = ReleaseControlService(store)
    deployment = service.request_test_deploy(manifest, "test", "ops", "ops-api-1").deployment
    assert service.transition(deployment.id, "VALIDATED", "validate").code == "ACCEPTED"
    return store, deployment.id


def test_ops_deployments_requires_global_release_permission(client, admin_user) -> None:
    def _limited_user() -> CurrentUser:
        return CurrentUser(user=admin_user, permissions=["release:view"], system_permissions=[])

    app.dependency_overrides[get_current_user] = _limited_user
    try:
        response = client.get("/api/v1/ops/deployments")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["msg"] == "缺少全局权限：release:view"


def test_ops_deployment_api_reads_persisted_store_and_orders_events(client, auth_headers, tmp_path, manifest) -> None:
    _, deployment_id = _configure_store(tmp_path, manifest)
    old_path = settings.release_control_database_path
    settings.release_control_database_path = str(tmp_path / "release-control.sqlite3")
    try:
        listed = client.get("/api/v1/ops/deployments", headers=auth_headers)
        detail = client.get(f"/api/v1/ops/deployments/{deployment_id}", headers=auth_headers)
        events = client.get(f"/api/v1/ops/deployments/{deployment_id}/events", headers=auth_headers)
    finally:
        settings.release_control_database_path = old_path

    assert listed.status_code == 200
    assert listed.json()["data"] == [
        {
            "id": deployment_id,
            "release_id": manifest.release_id,
            "manifest_sha256": manifest.manifest_sha256(),
            "environment": "test",
            "state": "VALIDATED",
            "created_at": listed.json()["data"][0]["created_at"],
        }
    ]
    assert detail.json()["data"]["id"] == deployment_id
    assert [event["sequence"] for event in events.json()["data"]] == [1, 2]
    assert events.json()["data"][1]["to_state"] == "VALIDATED"


def test_ops_deployments_fail_closed_when_store_is_not_configured(client, auth_headers) -> None:
    old_path = settings.release_control_database_path
    settings.release_control_database_path = ""
    try:
        response = client.get("/api/v1/ops/deployments", headers=auth_headers)
    finally:
        settings.release_control_database_path = old_path

    assert response.status_code == 503
    assert response.json()["detail"] == "release-control state store is not configured"
