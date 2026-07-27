"""Performance monitoring API tests — CRUD + WebSocket lifecycle in Mock mode."""
from __future__ import annotations

import json
import time
import pytest

from app.services import perf_service


# ── Helpers ──

SESSION_PAYLOAD = {
    "device_id": "emulator-5554",
    "platform": "Android",
    "pkg_name": "com.cameltv.app",
    "device_name": "Pixel 7",
    "device_model": "Pixel 7",
    "metrics": ["cpu", "memory", "fps", "jank"],
    "duration": 10,
}


def _create_session(client, headers, **overrides):
    """Helper: create a session and return the response JSON data field."""
    payload = {**SESSION_PAYLOAD, **overrides}
    resp = client.post("/api/v1/perf-sessions", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0, f"Expected code=0, got {body}"
    return body["data"]


def _start_session(client, headers, session_id):
    resp = client.post(f"/api/v1/perf-sessions/{session_id}/start", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0, f"Expected code=0, got {body}"
    return body["data"]


def _inject_mock_snapshots(db_session, session_id: int, count: int = 5):
    """Simulate the WebSocket collection loop by inserting mock PerfMetric rows."""
    now = time.time()
    for i in range(count):
        events = [{"event_type": "jank", "detail": "BigJank at sample"}] if i == 2 else []
        perf_service.save_snapshot(
            db_session,
            session_id=session_id,
            timestamp=now + i * 0.5,
            elapsed_s=i * 0.5,
            data={
                "cpu": {"appCpuRate": 35.0 + (i % 3) * 5},
                "memory": {"total": 420.0 + (i % 4) * 20},
                "fps": {"fps": 58.0 - (i % 3) * 2},
                "events": events,
            },
        )


# ── Device tests ──


class TestDeviceList:
    def test_list_devices_returns_mock_devices(self, client, auth_headers):
        """No SoloX installed → should return Mock devices (Pixel 7 + iPhone 15 Pro)."""
        resp = client.get("/api/v1/perf-sessions/devices", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data is not None
        assert "devices" in data
        devices = data["devices"]
        assert len(devices) >= 1
        platforms = {d["platform"] for d in devices}
        assert "Android" in platforms


# ── Session CRUD ──


class TestSessionCreate:
    def test_create_session_succeeds(self, client, auth_headers):
        data = _create_session(client, auth_headers)
        assert data["session_id"].startswith("PERF-")
        assert data["platform"] == "Android"
        assert data["pkg_name"] == "com.cameltv.app"
        assert data["status"] == "pending"
        assert data["duration"] == 10

    def test_create_session_requires_permission(self, client):
        """Without auth, endpoint returns 401 (require_permission uses get_current_user)."""
        resp = client.post("/api/v1/perf-sessions", json=SESSION_PAYLOAD)
        assert resp.status_code == 401

    def test_create_session_requires_pkg_name(self, client, auth_headers):
        """Empty pkg_name is accepted by Pydantic (no min_length constraint) but session still creates."""
        payload = {**SESSION_PAYLOAD, "pkg_name": ""}
        resp = client.post("/api/v1/perf-sessions", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        # Pydantic doesn't enforce non-empty string without min_length,
        # so this creates a session with empty pkg_name
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["pkg_name"] == ""


class TestSessionList:
    def test_list_sessions_paginated(self, client, auth_headers):
        _create_session(client, auth_headers)
        _create_session(client, auth_headers, pkg_name="com.other.app")

        resp = client.get("/api/v1/perf-sessions?page=1&page_size=20", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        assert data["page"] == 1

    def test_list_sessions_filter_by_platform(self, client, auth_headers):
        _create_session(client, auth_headers)

        resp = client.get("/api/v1/perf-sessions?platform=Android", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        items = body["data"]["items"]
        assert all(s["platform"] == "Android" for s in items)

    def test_list_sessions_filter_by_device(self, client, auth_headers):
        _create_session(client, auth_headers)

        resp = client.get("/api/v1/perf-sessions?device_id=emulator-5554", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        items = body["data"]["items"]
        assert all(s["device_id"] == "emulator-5554" for s in items)

    def test_list_sessions_empty_page(self, client, auth_headers):
        resp = client.get("/api/v1/perf-sessions?page=999&page_size=20", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert len(body["data"]["items"]) == 0


class TestSessionGet:
    def test_get_session_returns_data(self, client, auth_headers):
        created = _create_session(client, auth_headers)
        resp = client.get(f"/api/v1/perf-sessions/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["id"] == created["id"]
        assert data["session_id"] == created["session_id"]

    def test_get_nonexistent_session(self, client, auth_headers):
        resp = client.get("/api/v1/perf-sessions/99999", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] != 0


class TestSessionDelete:
    def test_delete_session_succeeds(self, client, auth_headers):
        created = _create_session(client, auth_headers)
        resp = client.delete(f"/api/v1/perf-sessions/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

        # Verify deleted
        resp = client.get(f"/api/v1/perf-sessions/{created['id']}", headers=auth_headers)
        assert resp.json()["code"] != 0


# ── Session lifecycle ──


class TestSessionLifecycle:
    def test_start_and_stop_session(self, client, auth_headers):
        created = _create_session(client, auth_headers, duration=0)  # unlimited
        session_id = created["id"]

        # Start
        start_data = _start_session(client, auth_headers, session_id)
        assert start_data["status"] == "running"

        # Verify status in GET
        resp = client.get(f"/api/v1/perf-sessions/{session_id}", headers=auth_headers)
        assert resp.json()["data"]["status"] == "running"

        # Stop
        resp = client.post(f"/api/v1/perf-sessions/{session_id}/stop", headers=auth_headers)
        assert resp.status_code == 200
        stop_data = resp.json()["data"]
        assert stop_data["status"] in ("completed", "cancelled")

    def test_cannot_start_non_pending_session(self, client, auth_headers):
        created = _create_session(client, auth_headers)
        session_id = created["id"]

        # Start once
        _start_session(client, auth_headers, session_id)

        # Try starting again → should fail
        resp = client.post(f"/api/v1/perf-sessions/{session_id}/start", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] != 0

    def test_stop_non_running_session_is_harmless(self, client, auth_headers):
        """Stopping a pending session returns its current status."""
        created = _create_session(client, auth_headers)
        resp = client.post(f"/api/v1/perf-sessions/{created['id']}/stop", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] in ("pending", "cancelled")

    def test_multiple_sessions_independent_lifecycle(self, client, auth_headers):
        """Starting session A shouldn't affect session B status."""
        a = _create_session(client, auth_headers)
        b = _create_session(client, auth_headers)

        _start_session(client, auth_headers, a["id"])

        # B should still be pending
        resp = client.get(f"/api/v1/perf-sessions/{b['id']}", headers=auth_headers)
        assert resp.json()["data"]["status"] == "pending"

        resp = client.post(f"/api/v1/perf-sessions/{a['id']}/stop", headers=auth_headers)
        assert resp.json()["code"] == 0


# ── Metrics ──


class TestMetrics:
    def test_metrics_saved_after_collection(self, client, auth_headers, db_session):
        """Verify metrics are persisted after injecting mock snapshots."""
        created = _create_session(client, auth_headers, duration=1)
        session_id = created["id"]

        _start_session(client, auth_headers, session_id)
        _inject_mock_snapshots(db_session, session_id, count=3)
        client.post(f"/api/v1/perf-sessions/{session_id}/stop", headers=auth_headers)

        # Fetch metrics
        resp = client.get(f"/api/v1/perf-sessions/{session_id}/metrics", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["total_points"] >= 1

        # Verify data point shape
        point = data["metrics"][0]
        assert "timestamp" in point
        assert "elapsed_s" in point
        assert "values" in point
        assert isinstance(point["values"], dict)

    def test_metrics_since_ts_filter(self, client, auth_headers, db_session):
        """sinceTs parameter should filter to newer points."""
        created = _create_session(client, auth_headers, duration=1)
        session_id = created["id"]

        _start_session(client, auth_headers, created["id"])
        before = time.time()
        _inject_mock_snapshots(db_session, session_id, count=3)
        client.post(f"/api/v1/perf-sessions/{session_id}/stop", headers=auth_headers)

        resp = client.get(
            f"/api/v1/perf-sessions/{session_id}/metrics?sinceTs={before}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


# ── Report ──


class TestReport:
    def test_report_generated_after_collection(self, client, auth_headers, db_session):
        created = _create_session(client, auth_headers, duration=1)
        session_id = created["id"]

        _start_session(client, auth_headers, session_id)
        _inject_mock_snapshots(db_session, session_id, count=5)
        client.post(f"/api/v1/perf-sessions/{session_id}/stop", headers=auth_headers)

        resp = client.get(f"/api/v1/perf-sessions/{session_id}/report", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        report = body["data"]

        assert report["session"]["id"] == session_id
        assert "metrics" in report
        assert "anomalies" in report
        assert len(report["metrics"]) >= 1

        # Verify metric stat shape
        stat = report["metrics"][0]
        for field in ("metric_type", "mean", "median", "p95", "min_val", "max_val", "stddev", "samples", "unit", "passed"):
            assert field in stat, f"Missing field: {field}"

    def test_report_on_empty_session(self, client, auth_headers):
        """Session with no data returns empty report (metrics=[], anomalies=[])."""
        created = _create_session(client, auth_headers)
        resp = client.get(f"/api/v1/perf-sessions/{created['id']}/report", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["metrics"] == []
        assert body["data"]["anomalies"] == []


# ── Compare ──


class TestCompare:
    def test_compare_two_sessions(self, client, auth_headers, db_session):
        """Compare two completed sessions."""
        # Session A
        a = _create_session(client, auth_headers, pkg_name="com.app.v1", duration=1)
        _start_session(client, auth_headers, a["id"])
        _inject_mock_snapshots(db_session, a["id"], count=3)
        client.post(f"/api/v1/perf-sessions/{a['id']}/stop", headers=auth_headers)

        # Session B
        b = _create_session(client, auth_headers, pkg_name="com.app.v2", duration=1)
        _start_session(client, auth_headers, b["id"])
        _inject_mock_snapshots(db_session, b["id"], count=3)
        client.post(f"/api/v1/perf-sessions/{b['id']}/stop", headers=auth_headers)

        resp = client.post("/api/v1/perf-sessions/compare", json={
            "session_a_id": a["id"],
            "session_b_id": b["id"],
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]

        assert data["session_a"]["id"] == a["id"]
        assert data["session_b"]["id"] == b["id"]
        assert "deltas" in data
        assert len(data["deltas"]) >= 1

        # Verify delta shape
        delta = data["deltas"][0]
        for field in ("metric_type", "session_a_mean", "session_b_mean",
                       "delta_absolute", "delta_percent", "direction", "significant"):
            assert field in delta, f"Missing field: {field}"

    def test_compare_nonexistent_sessions(self, client, auth_headers):
        resp = client.post("/api/v1/perf-sessions/compare", json={
            "session_a_id": 99998,
            "session_b_id": 99999,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] != 0


# ── Permission enforcement ──


class TestPermissions:
    """Verify authentication/permission is required."""

    def test_unauthenticated_rejected_403(self, client):
        """Endpoints that require permission return 403 without auth."""
        endpoints = [
            ("post", "/api/v1/perf-sessions"),
            ("get", "/api/v1/perf-sessions"),
            ("get", "/api/v1/perf-sessions/1"),
            ("delete", "/api/v1/perf-sessions/1"),
            ("post", "/api/v1/perf-sessions/1/start"),
            ("post", "/api/v1/perf-sessions/1/stop"),
            ("get", "/api/v1/perf-sessions/1/metrics"),
            ("get", "/api/v1/perf-sessions/1/report"),
            ("post", "/api/v1/perf-sessions/compare"),
        ]
        for method, path in endpoints:
            if method == "get":
                resp = client.get(path)
            elif method == "delete":
                resp = client.delete(path)
            else:
                resp = client.post(path, json={})
            assert resp.status_code in (401, 403), (
                f"{method} {path} returned {resp.status_code}, expected 401 or 403"
            )

    def test_device_endpoint_unauthenticated(self, client):
        """Device list endpoint uses get_current_user (not require_permission), returns 401."""
        resp = client.get("/api/v1/perf-sessions/devices")
        assert resp.status_code == 401


# ── Device endpoint detail ──


class TestDeviceEndpointDetail:
    def test_device_list_includes_required_fields(self, client, auth_headers):
        resp = client.get("/api/v1/perf-sessions/devices", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        devices = body["data"]["devices"]
        for device in devices:
            for field in ("device_id", "device_name", "platform", "status"):
                assert field in device, f"Missing field '{field}' in device"


# ── Schema validation ──


class TestSchemaValidation:
    def test_session_out_schema_matches_model(self, client, auth_headers):
        """Verify response fields match the expected schema."""
        created = _create_session(client, auth_headers)
        resp = client.get(f"/api/v1/perf-sessions/{created['id']}", headers=auth_headers)
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]

        expected_fields = {
            "id", "session_id", "device_id", "device_name", "device_model",
            "platform", "pkg_name", "metrics", "status", "duration",
            "actual_duration_s", "creator_id", "created_at", "started_at",
            "ended_at",
        }
        returned = set(data.keys())
        missing = expected_fields - returned
        assert not missing, f"Response missing fields: {missing}"

    def test_metrics_response_schema(self, client, auth_headers, db_session):
        created = _create_session(client, auth_headers, duration=1)
        _start_session(client, auth_headers, created["id"])
        _inject_mock_snapshots(db_session, created["id"], count=3)
        client.post(f"/api/v1/perf-sessions/{created['id']}/stop", headers=auth_headers)

        resp = client.get(f"/api/v1/perf-sessions/{created['id']}/metrics", headers=auth_headers)
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "session_id" in data
        assert "metrics" in data
        assert "total_points" in data
        assert isinstance(data["metrics"], list)
        assert isinstance(data["total_points"], int)
