"""Batch 208 (C4) — store-backed smart-regression snapshot loader tests."""
from __future__ import annotations

import pytest

from app.modules.aitde import data as _data_pkg  # noqa: F401  registers data tables
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.execution.models import EnvironmentSnapshot
from app.modules.aitde.smart_regression.providers import (
    _default_loader as load,
)


def test_env_snapshot_ref_loads_service_versions(db):
    snap = EnvironmentSnapshot(
        environment_id=1,
        mission_id=1,
        service_versions_json='{"svc-a": "v1"}',
        fingerprint_hash="h",
    )
    db.add(snap)
    db.commit()
    out = load(db, 1, f"env_snapshot:{snap.id}", "ENVIRONMENT")
    assert out == {"svc-a": {"value": "v1", "sensitivity": "public"}}


def test_env_snapshot_missing_raises(db):
    with pytest.raises(ValueError, match="not found"):
        load(db, 1, "env_snapshot:9999", "ENVIRONMENT")


def test_data_source_ref_loads_config(db):
    src = DataSource(
        project_id=1,
        source_type="STATIC",
        name="spec-store",
        config_json='{"paths": {"/users": "get"}}',
    )
    db.add(src)
    db.commit()
    out = load(db, 1, f"data_source:{src.id}:OPENAPI", "OPENAPI")
    assert out == {"paths": {"/users": "get"}}


def test_data_source_unknown_kind_raises(db):
    with pytest.raises(ValueError, match="unsupported data_source kind"):
        load(db, 1, "data_source:1:UNKNOWN", "OPENAPI")


def test_unresolved_ref_raises_with_supported_formats(db):
    with pytest.raises(ValueError, match="supported"):
        load(db, 1, "store://x", "OPENAPI")
