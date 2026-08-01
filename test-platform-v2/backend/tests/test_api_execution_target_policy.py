from __future__ import annotations

import httpx


ASSERTIONS = [{"type": "status_code", "operator": "eq", "expected": 200}]


def _seed_environment(db_session, *, project_id: int, base_url: str, env_type: str = "test"):
    from app.models.environment import Environment

    env = Environment(
        project_id=project_id,
        name=f"env-{project_id}",
        env_type=env_type,
        is_production=env_type == "prod",
        base_url=base_url,
    )
    db_session.add(env)
    db_session.commit()
    return env


def test_cross_project_environment_is_rejected_before_network(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    env = _seed_environment(db_session, project_id=2, base_url="https://other.example.test")
    network_calls = 0

    def fail_if_called(*_args, **_kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("network must not be called")

    monkeypatch.setattr(httpx.Client, "request", fail_if_called)
    result = quick_execute(
        db_session,
        {"method": "GET", "url": "/health"},
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
    )

    assert result["error_type"] == "TARGET_POLICY"
    assert network_calls == 0


def test_absolute_url_must_match_environment_host(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    env = _seed_environment(db_session, project_id=1, base_url="https://allowed.example.test")
    monkeypatch.setattr(
        httpx.Client,
        "request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network must not be called")),
    )

    result = quick_execute(
        db_session,
        {"method": "GET", "url": "https://blocked.example.test/data"},
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
    )

    assert result["error_type"] == "TARGET_POLICY"
    assert "environment host" in result["error"]


def test_private_host_requires_and_uses_explicit_environment_policy(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    env = _seed_environment(db_session, project_id=1, base_url="http://10.61.0.5")
    seen: list[str] = []

    def fake_request(_client, method, url, **_kwargs):
        seen.append(str(url))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    result = quick_execute(
        db_session,
        {"method": "GET", "url": "/health"},
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
    )

    assert result["all_pass"] is True
    assert seen == ["http://10.61.0.5/health"]


def test_redirect_target_is_revalidated_before_second_hop(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    env = _seed_environment(db_session, project_id=1, base_url="https://allowed.example.test")
    seen: list[str] = []

    def fake_request(_client, method, url, **_kwargs):
        seen.append(str(url))
        return httpx.Response(
            302,
            headers={"Location": "https://blocked.example.test/secret"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    result = quick_execute(
        db_session,
        {"method": "GET", "url": "/redirect"},
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
    )

    assert result["error_type"] == "TARGET_POLICY"
    assert seen == ["https://allowed.example.test/redirect"]


def test_production_write_denial_happens_before_network(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    env = _seed_environment(
        db_session,
        project_id=1,
        base_url="https://prod.example.test",
        env_type="prod",
    )
    network_calls = 0

    def fail_if_called(*_args, **_kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("network must not be called")

    monkeypatch.setattr(httpx.Client, "request", fail_if_called)
    result = quick_execute(
        db_session,
        {"method": "POST", "url": "/write", "body": "{}"},
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
        confirm_prod=False,
        has_execute_prod=True,
    )

    assert result["error_type"] == "POLICY_DENIED"
    assert network_calls == 0
