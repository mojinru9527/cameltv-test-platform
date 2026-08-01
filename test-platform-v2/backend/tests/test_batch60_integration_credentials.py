from __future__ import annotations

import json

from app.core.cipher import decrypt_value
from app.models.integration import IntegrationConfig


def test_partial_integration_auth_update_preserves_existing_credentials(
    client,
    auth_headers,
    db_session,
) -> None:
    original = {
        "email": "batch60@example.test",
        "api_token": "batch60-existing-token",
        "project_key": "OLD",
    }
    created = client.post(
        "/api/v1/integrations",
        json={
            "name": "Batch 60 Jira credential preservation",
            "provider_type": "jira",
            "base_url": "https://jira.example.test",
            "auth_json": json.dumps(original),
            "enabled": False,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200
    integration_id = created.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/integrations/{integration_id}",
        json={"name": "Renamed", "auth_json": json.dumps({"project_key": "CAMEL"})},
        headers=auth_headers,
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["auth_json"] == "********"
    db_session.expire_all()
    row = db_session.get(IntegrationConfig, integration_id)
    persisted = json.loads(decrypt_value(row.auth_json))
    assert persisted == {
        "email": "batch60@example.test",
        "api_token": "batch60-existing-token",
        "project_key": "CAMEL",
    }


def test_blank_partial_integration_auth_values_do_not_clear_existing_secret(
    client,
    auth_headers,
    db_session,
) -> None:
    created = client.post(
        "/api/v1/integrations",
        json={
            "name": "Batch 60 TAPD credential preservation",
            "provider_type": "tapd",
            "base_url": "https://tapd.example.test",
            "auth_json": json.dumps({
                "api_user": "batch60-user",
                "api_password": "batch60-password",
                "workspace_id": "123",
            }),
            "enabled": False,
        },
        headers=auth_headers,
    )
    integration_id = created.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/integrations/{integration_id}",
        json={"auth_json": json.dumps({"api_user": "", "api_password": ""})},
        headers=auth_headers,
    )

    assert updated.status_code == 200
    db_session.expire_all()
    row = db_session.get(IntegrationConfig, integration_id)
    assert json.loads(decrypt_value(row.auth_json)) == {
        "api_user": "batch60-user",
        "api_password": "batch60-password",
        "workspace_id": "123",
    }
