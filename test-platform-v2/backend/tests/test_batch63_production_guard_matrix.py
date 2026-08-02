"""Batch 63 Slice 3 — 多入口生产保护统一矩阵（B60-P0-004 / B60-P1-019）。

覆盖 quick / asset / single / group / batch 五类 API 执行入口：
- 生产环境写操作缺少 confirm_prod=true → HTTP 400，零网络、零持久化副作用；
- 跨项目环境 → HTTP 404，零持久化副作用；
- 非生产环境不要求 confirm（只读基线）。
"""

from __future__ import annotations

import httpx
from unittest.mock import patch

from app.models.api_asset import ApiExecutionTask
from app.models.environment import Environment
from app.models.test_case import TestCase


def _seed_prod_env(db_session, *, project_id: int = 1) -> Environment:
    env = Environment(
        project_id=project_id,
        name="Prod matrix env",
        env_type="prod",
        is_production=True,
        base_url="https://prod.example.invalid",
    )
    db_session.add(env)
    db_session.flush()
    return env


def _quick_payload(*, source: str, env_id: int, method: str = "POST") -> dict:
    return {
        "source": source,
        "environment_id": env_id,
        "confirm_prod": False,
        "request": {
            "method": method,
            "url": "/write",
            "headers": {},
            "body": '{"k": 1}',
            "query_params": {},
            "assertions": [],
        },
    }


def test_quick_execute_prod_write_without_confirm_rejected_before_network(
    client, auth_headers, db_session,
):
    env = _seed_prod_env(db_session)

    resp = client.post(
        "/api/v1/apitest/api-execute",
        headers=auth_headers,
        json=_quick_payload(source="quick", env_id=env.id),
    )

    assert resp.status_code == 400
    assert "confirm_prod" in resp.json()["msg"]


def test_asset_execute_prod_write_without_confirm_rejected_before_network(
    client, auth_headers, db_session,
):
    env = _seed_prod_env(db_session)

    resp = client.post(
        "/api/v1/apitest/api-execute",
        headers=auth_headers,
        json=_quick_payload(source="asset", env_id=env.id),
    )

    assert resp.status_code == 400
    assert "confirm_prod" in resp.json()["msg"]


def test_single_case_execute_prod_write_without_confirm_rejected_without_execution(
    client, auth_headers, db_session,
):
    env = _seed_prod_env(db_session)
    case = TestCase(
        project_id=1,
        title="Matrix single case",
        case_type="api",
        api_method="POST",
        api_endpoint="/write",
    )
    db_session.add(case)
    db_session.commit()

    with patch(
        "app.api.v1.test_case.execute_api_case",
        return_value={"all_pass": True},
    ) as execute:
        resp = client.post(
            f"/api/v1/test-cases/{case.id}/execute",
            headers=auth_headers,
            json={"environment_id": env.id, "confirm_prod": False},
        )

    assert resp.status_code == 200
    assert resp.json()["code"] == 400
    assert "confirm_prod" in resp.json()["msg"]
    execute.assert_not_called()


def test_task_create_prod_env_without_confirm_rejected_with_zero_rows(
    client, auth_headers, db_session,
):
    env = _seed_prod_env(db_session)
    case = TestCase(
        project_id=1,
        title="Matrix task case",
        case_type="api",
        api_method="POST",
        api_endpoint="/write",
    )
    db_session.add(case)
    db_session.commit()

    resp = client.post(
        "/api/v1/apitest/tasks",
        headers=auth_headers,
        json={
            "name": "prod task without confirm",
            "case_ids": [case.id],
            "environment_id": env.id,
            "confirm_prod": False,
        },
    )

    assert resp.status_code == 400
    assert "confirm_prod" in resp.json()["detail"]
    assert db_session.query(ApiExecutionTask).count() == 0


def test_task_create_foreign_project_env_rejected_with_zero_rows(
    client, auth_headers, db_session,
):
    foreign_env = Environment(
        project_id=2,
        name="Foreign env",
        env_type="test",
        base_url="https://other.example.invalid",
    )
    case = TestCase(
        project_id=1,
        title="Matrix foreign env case",
        case_type="api",
        api_method="GET",
        api_endpoint="/read",
    )
    db_session.add_all([foreign_env, case])
    db_session.commit()

    resp = client.post(
        "/api/v1/apitest/tasks",
        headers=auth_headers,
        json={
            "name": "foreign env task",
            "case_ids": [case.id],
            "environment_id": foreign_env.id,
            "confirm_prod": True,
        },
    )

    assert resp.status_code == 404
    assert db_session.query(ApiExecutionTask).count() == 0


def test_quick_execute_test_env_write_does_not_require_confirm(
    client, auth_headers, db_session, monkeypatch,
):
    env = Environment(
        project_id=1,
        name="Test env",
        env_type="test",
        base_url="https://test.example.invalid",
    )
    db_session.add(env)
    db_session.commit()

    seen: list[str] = []

    class FakeHttpxClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def request(self, method, url, **kwargs):
            seen.append(str(url))
            return httpx.Response(
                200,
                json={"ok": True},
                request=httpx.Request(method, url),
            )

    monkeypatch.setattr(
        "app.services.api_execution_service.httpx.Client",
        FakeHttpxClient,
    )
    resp = client.post(
        "/api/v1/apitest/api-execute",
        headers=auth_headers,
        json={
            **_quick_payload(source="quick", env_id=env.id, method="GET"),
            "request": {
                **_quick_payload(source="quick", env_id=env.id, method="GET")["request"],
                "assertions": [{"type": "status_code", "operator": "eq", "expected": 200}],
            },
        },
    )

    assert resp.status_code == 200
    assert seen == ["https://test.example.invalid/write"]
