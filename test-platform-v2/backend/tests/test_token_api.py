"""Batch 127 — API Token scope serialization and legacy compatibility."""
from __future__ import annotations


def test_create_token_persists_json_scopes(client, auth_headers, db_session):
    from app.models.api_token import ApiToken

    response = client.post(
        "/api/v1/tokens",
        json={"name": "B127 token", "scopes": ["trigger", "api"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scopes"] == ["trigger", "api"]
    row = db_session.get(ApiToken, data["id"])
    assert row.scopes == '["trigger", "api"]'


def test_list_token_normalizes_legacy_python_repr(client, auth_headers, db_session):
    from app.models.api_token import ApiToken

    _, token_hash = ApiToken.generate()
    db_session.add(ApiToken(
        project_id=1,
        name="legacy",
        token_hash=token_hash,
        token_prefix="legacy-prefix",
        scopes="['trigger', 'api']",
        enabled=True,
    ))
    db_session.commit()

    response = client.get("/api/v1/tokens", headers=auth_headers)

    assert response.status_code == 200
    legacy = next(item for item in response.json()["data"] if item["name"] == "legacy")
    assert legacy["scopes"] == ["trigger", "api"]
