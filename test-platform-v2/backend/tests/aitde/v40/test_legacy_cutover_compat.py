"""AITDE V4.0 (V40-006/007) TestPlan/Dataset cutover policy + compat tests."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.exceptions import APIException
from app.modules.aitde.data.models import LegacyDatasetLink
from app.modules.aitde.legacy_cutover.models import LegacyObjectMapping
from app.modules.aitde.legacy_cutover.service import (
    CompatibilityPolicy,
    LegacyCutoverCompatService,
)


def test_testplan_write_stage_gate(monkeypatch):
    monkeypatch.setattr(settings, "test_plan_write_stage", "READONLY")
    with pytest.raises(APIException) as exc:
        CompatibilityPolicy.enforce_v1_write("test-plan")
    assert exc.value.http_status == 410
    monkeypatch.setattr(settings, "test_plan_write_stage", "ACTIVE")
    CompatibilityPolicy.enforce_v1_write("test-plan")  # no raise


def test_dataset_write_stage_gate(monkeypatch):
    monkeypatch.setattr(settings, "dataset_write_stage", "READONLY")
    with pytest.raises(APIException) as exc:
        CompatibilityPolicy.enforce_v1_write("dataset")
    assert exc.value.http_status == 410
    monkeypatch.setattr(settings, "dataset_write_stage", "ACTIVE")
    CompatibilityPolicy.enforce_v1_write("dataset")


def test_unknown_surface_rejected(monkeypatch):
    with pytest.raises(ValueError):
        CompatibilityPolicy.v1_write_stage("whoknows")


def test_resolve_testplan_via_mapping(db):
    m = LegacyObjectMapping(
        project_id=1,
        legacy_type="TEST_PLAN",
        legacy_id=42,
        canonical_type="EXECUTION_CAMPAIGN",
        canonical_id=9,
        migration_status="VERIFIED",
    )
    db.add(m)
    db.commit()
    resolved = LegacyCutoverCompatService.resolve(db, 1, "test-plan", 42)
    assert resolved["canonical_type"] == "EXECUTION_CAMPAIGN"
    assert resolved["canonical_id"] == 9
    assert resolved["migration_status"] == "VERIFIED"


def test_resolve_dataset_via_legacy_link(db):
    link = LegacyDatasetLink(data_source_id=7, legacy_dataset_id=55)
    db.add(link)
    db.commit()
    resolved = LegacyCutoverCompatService.resolve(db, 1, "dataset", 55)
    assert resolved["canonical_type"] == "DATA_SOURCE"
    assert resolved["canonical_id"] == 7


def test_resolve_unmapped_returns_none(db):
    resolved = LegacyCutoverCompatService.resolve(db, 1, "test-plan", 9999)
    assert resolved["canonical"] is None
