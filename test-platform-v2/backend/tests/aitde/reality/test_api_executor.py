"""V3.9-R2 DATA-002 — ApiFixtureExecutor real HTTP POST + VERIFY.

Verifies the API_BUILDER strategy performs a real POST, extracts the physical id,
and GET-verifies the created resource before a physical effect is accepted. A
200/201 create with no real resource behind it must NOT be accepted (VERIFY_MISMATCH).
"""
from __future__ import annotations

import httpx
import pytest

from app.modules.aitde.data.executors.api_executor import ApiFixtureExecutor
from app.modules.aitde.drivers.http.data_api_driver import DataApiDriver, DataApiError


class _FakeApiDriver:
    """Records POST/GET/DELETE calls and returns canned responses."""

    def __init__(self, create_result=None, get_result=None, get_status=200):
        self.create_result = create_result or {}
        self.get_result = get_result or {}
        self.get_status = get_status
        self.posted = None
        self.get_called = None

    def post(self, path, payload):
        self.posted = (path, payload)
        return (201, self.create_result)

    def get(self, path):
        self.get_called = path
        return (self.get_status, self.get_result)

    def delete(self, path):
        return 204


def test_execute_create_posts_and_verifies_physical_id():
    driver = _FakeApiDriver(create_result={"id": 42, "name": "alice"}, get_result={"id": 42, "status": "ACTIVE"})
    result = ApiFixtureExecutor.execute_create(
        driver, "/memberships", {"name": "alice"}, get_endpoint="/memberships/{id}", id_field="id"
    )
    assert result["created"] is True
    assert result["physical_id"] == 42
    assert driver.posted == ("/memberships", {"name": "alice"})
    assert driver.get_called == "/memberships/42"


def test_execute_create_uses_default_verify_path_when_no_template():
    driver = _FakeApiDriver(
        create_result={"record": {"id": "x-9"}}, get_result={"record": {"id": "x-9"}}
    )
    result = ApiFixtureExecutor.execute_create(
        driver, "/memberships", {"name": "bob"}, id_field="record.id"
    )
    assert result["physical_id"] == "x-9"
    assert driver.get_called == "/memberships/x-9"


def test_execute_create_rejects_when_id_missing():
    driver = _FakeApiDriver(create_result={"ok": True})
    with pytest.raises(DataApiError) as exc:
        ApiFixtureExecutor.execute_create(driver, "/memberships", {"name": "alice"})
    assert exc.value.code == "NO_ID"


def test_execute_create_rejects_when_verify_mismatches():
    driver = _FakeApiDriver(create_result={"id": 7}, get_result={})
    with pytest.raises(DataApiError) as exc:
        ApiFixtureExecutor.execute_create(driver, "/memberships", {"name": "alice"})
    assert exc.value.code == "VERIFY_MISMATCH"


def test_execute_create_rejects_empty_payload():
    driver = _FakeApiDriver(create_result={"id": 1}, get_result={"id": 1})
    with pytest.raises(DataApiError) as exc:
        ApiFixtureExecutor.execute_create(driver, "/memberships", {})
    assert exc.value.code == "EMPTY_PAYLOAD"


# ────────────────────────────────────────────────────────────────────────────
# DataApiDriver (transport) — real httpx round-trip via MockTransport
# ────────────────────────────────────────────────────────────────────────────


def _driver_with(transport):
    return DataApiDriver(
        {"base_url": "http://svc.test", "auth_scheme": "Bearer"}, "SECRET_KEY", transport=transport
    )


def test_api_driver_post_sends_auth_and_parses_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer SECRET_KEY"
        assert request.method == "POST"
        return httpx.Response(201, json={"id": 3, "status": "ACTIVE"})

    driver = _driver_with(httpx.MockTransport(handler))
    status, data = driver.post("/memberships", {"name": "alice"})
    assert status == 201
    assert data["id"] == 3


def test_api_driver_post_rejects_non_2xx():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "bad"})

    driver = _driver_with(httpx.MockTransport(handler))
    with pytest.raises(DataApiError) as exc:
        driver.post("/memberships", {"name": "alice"})
    assert exc.value.code == "CREATE_REJECTED"


def test_api_driver_get_404_is_verify_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "missing"})

    driver = _driver_with(httpx.MockTransport(handler))
    with pytest.raises(DataApiError) as exc:
        driver.get("/memberships/42")
    assert exc.value.code == "VERIFY_FAILED"


def test_api_driver_delete_returns_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    driver = _driver_with(httpx.MockTransport(handler))
    assert driver.delete("/memberships/42") == 204
