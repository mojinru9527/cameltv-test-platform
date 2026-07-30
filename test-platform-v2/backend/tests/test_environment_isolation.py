"""Project and parent-resource isolation for environment variables."""
from __future__ import annotations

from app.core.cipher import encrypt_value
from app.models.environment import Environment, EnvironmentVariable


def _seed_environments(db_session) -> tuple[Environment, Environment, EnvironmentVariable]:
    own = Environment(
        project_id=1,
        name="own",
        env_type="test",
        base_url="https://own.example.test",
    )
    foreign = Environment(
        project_id=2,
        name="foreign",
        env_type="test",
        base_url="https://foreign.example.test",
    )
    db_session.add_all([own, foreign])
    db_session.flush()
    foreign_variable = EnvironmentVariable(
        environment_id=foreign.id,
        key="SECRET_TOKEN",
        value=encrypt_value("must-not-leak"),
        encrypted=True,
    )
    db_session.add(foreign_variable)
    db_session.commit()
    return own, foreign, foreign_variable


def test_foreign_environment_cannot_be_updated_or_deleted(
    client, auth_headers, db_session,
) -> None:
    _, foreign, _ = _seed_environments(db_session)

    updated = client.put(
        f"/api/v1/environments/{foreign.id}",
        headers=auth_headers,
        json={"name": "stolen"},
    )
    deleted = client.delete(
        f"/api/v1/environments/{foreign.id}",
        headers=auth_headers,
    )

    assert updated.status_code == 404
    assert deleted.status_code == 404
    db_session.expire_all()
    assert db_session.get(Environment, foreign.id).name == "foreign"


def test_foreign_environment_variables_are_not_visible_or_resolvable(
    client, auth_headers, db_session,
) -> None:
    _, foreign, _ = _seed_environments(db_session)

    listed = client.get(
        f"/api/v1/environments/{foreign.id}/variables",
        headers=auth_headers,
    )
    created = client.post(
        f"/api/v1/environments/{foreign.id}/variables",
        headers=auth_headers,
        json={"key": "NEW_SECRET", "value": "new-value", "encrypted": True},
    )
    resolved = client.post(
        "/api/v1/environments/resolve",
        headers=auth_headers,
        json={
            "environment_id": foreign.id,
            "template": "Bearer ${SECRET_TOKEN}",
        },
    )

    assert listed.status_code == 404
    assert created.status_code == 404
    assert resolved.status_code == 404
    assert "must-not-leak" not in resolved.text
    assert "SECRET_TOKEN" not in resolved.text


def test_variable_id_must_belong_to_environment_and_project(
    client, auth_headers, db_session,
) -> None:
    own, foreign, foreign_variable = _seed_environments(db_session)

    updated = client.put(
        f"/api/v1/environments/{own.id}/variables/{foreign_variable.id}",
        headers=auth_headers,
        json={"value": "stolen"},
    )
    deleted = client.delete(
        f"/api/v1/environments/{own.id}/variables/{foreign_variable.id}",
        headers=auth_headers,
    )

    assert updated.status_code == 404
    assert deleted.status_code == 404
    db_session.expire_all()
    variable = db_session.get(EnvironmentVariable, foreign_variable.id)
    assert variable is not None
    assert variable.environment_id == foreign.id


def test_environment_routes_require_an_explicit_project(
    client, auth_headers, db_session,
) -> None:
    own, _, _ = _seed_environments(db_session)
    headers_without_project = {
        key: value
        for key, value in auth_headers.items()
        if key.lower() != "x-project-id"
    }

    listed = client.get("/api/v1/environments", headers=headers_without_project)
    variables = client.get(
        f"/api/v1/environments/{own.id}/variables",
        headers=headers_without_project,
    )

    assert listed.status_code == 403
    assert variables.status_code == 403
