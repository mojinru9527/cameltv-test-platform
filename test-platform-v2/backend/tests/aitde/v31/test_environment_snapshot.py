"""AITDE V3.1 environment snapshot + fingerprint tests (V31-001/V31-005)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.environment import snapshot_service
from app.modules.aitde.environment.fingerprint import compute_fingerprint_hash


def _data(**overrides):
    data = {
        "build_label": "v3.1-test",
        "frontend_version": "14.1.0",
        "service_versions": {"api": "1.0.0", "web": "2.0.0"},
        "openapi_hash": "abc123",
    }
    data.update(overrides)
    return data


def test_fingerprint_is_stable_and_order_independent():
    a = compute_fingerprint_hash(service_versions={"api": "1.0.0", "web": "2.0.0"})
    b = compute_fingerprint_hash(service_versions={"web": "2.0.0", "api": "1.0.0"})
    assert a == b
    assert len(a) == 64


def test_fingerprint_changes_on_sensitive_factor():
    a = compute_fingerprint_hash(frontend_version="14.1.0")
    b = compute_fingerprint_hash(frontend_version="14.1.1")
    assert a != b


def test_capture_snapshot_generates_hash(db):
    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=5, project_id=1, data=_data()
    )
    assert len(snap.fingerprint_hash) == 64
    assert snap.created_by_type == "MANUAL"  # build_label provided


def test_capture_without_build_label_is_auto(db):
    data = _data()
    data["build_label"] = None
    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=5, project_id=1, data=data
    )
    assert snap.created_by_type == "AUTO"


def test_capture_rejects_empty_environment(db):
    with pytest.raises(APIException) as exc:
        snapshot_service.capture_snapshot(
            db, environment_id=0, mission_id=5, project_id=1, data=_data()
        )
    assert exc.value.http_status == 400
