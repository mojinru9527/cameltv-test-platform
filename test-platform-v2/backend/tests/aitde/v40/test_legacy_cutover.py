"""AITDE V4.0 (V40-001/002) Legacy Cutover service tests."""

from __future__ import annotations

import pytest

from app.modules.aitde.legacy_cutover import service
from app.modules.aitde.legacy_cutover.models import (
    LegacyObjectMapping,
    LegacyUsageRecord,
)


# ── V40-001 Legacy Usage Inventory ──────────────────────────────────────────


def test_record_usage_creates_and_increments(db):
    inv = service.LegacyUsageInventoryService
    first = inv.record(
        db,
        1,
        {
            "consumer_type": "INTERNAL",
            "surface_kind": "ENDPOINT",
            "path": "/api/v1/test-cases",
            "method": "GET",
            "object_type": "TEST_CASE",
            "owner": "frontend",
            "replacement_v2": "/api/v2/scenarios",
        },
    )
    assert first["id"] > 0
    assert first["deprecation_stage"] == "ACTIVE"
    assert first["traffic_count"] == 1

    second = inv.record(
        db,
        1,
        {
            "consumer_type": "INTERNAL",
            "surface_kind": "ENDPOINT",
            "path": "/api/v1/test-cases",
            "method": "GET",
            "object_type": "TEST_CASE",
            "owner": "frontend",
            "replacement_v2": "/api/v2/scenarios",
        },
    )
    # Idempotent upsert: same surface bumps traffic, no duplicate row.
    assert second["id"] == first["id"]
    assert second["traffic_count"] == 2
    count = db.query(LegacyUsageRecord).count()
    assert count == 1


def test_unknown_consumers_reporting(db):
    inv = service.LegacyUsageInventoryService
    inv.record(
        db,
        1,
        {"consumer_type": "UNKNOWN", "path": "/x", "method": "GET", "object_type": "API_TEST"},
    )
    inv.record(
        db,
        1,
        {"consumer_type": "INTERNAL", "path": "/y", "method": "POST", "object_type": "UI_TEST"},
    )
    unknown = inv.unknown_consumers(db, 1)
    assert len(unknown) == 1
    assert unknown[0]["consumer_type"] == "UNKNOWN"


def test_invalid_consumer_type_rejected(db):
    with pytest.raises(ValueError):
        service.LegacyUsageInventoryService.record(
            db, 1, {"consumer_type": "BOGUS", "path": "/z", "method": "GET"}
        )


# ── V40-002 Legacy Object Mapping ───────────────────────────────────────────


def test_mapping_upsert_is_idempotent(db):
    m = service.LegacyObjectMappingService
    row = m.upsert(
        db, 1, {"legacy_type": "TEST_CASE", "legacy_id": 100, "canonical_type": "SCENARIO", "canonical_id": 7}
    )
    assert row["migration_status"] == "MAPPED"
    assert row["legacy_id"] == 100

    # Same (legacy_type, legacy_id) updates, not duplicates.
    row2 = m.upsert(
        db, 1, {"legacy_type": "TEST_CASE", "legacy_id": 100, "canonical_type": "SCENARIO", "canonical_id": 8}
    )
    assert row2["id"] == row["id"]
    assert row2["canonical_id"] == 8
    assert db.query(LegacyObjectMapping).count() == 1


def test_mapping_verify_sets_verified_at(db):
    m = service.LegacyObjectMappingService
    row = m.upsert(
        db, 1, {"legacy_type": "TEST_PLAN", "legacy_id": 2, "canonical_type": "CAMPAIGN", "canonical_id": 3}
    )
    verified = m.verify(db, row["id"])
    assert verified["migration_status"] == "VERIFIED"
    assert verified["verified_at"] is not None


def test_mapping_invalid_legacy_type_rejected(db):
    with pytest.raises(ValueError):
        service.LegacyObjectMappingService.upsert(
            db, 1, {"legacy_type": "NOPE", "legacy_id": 1, "canonical_type": "X", "canonical_id": 1}
        )


# ── V40-002 Cutover Batch ───────────────────────────────────────────────────


def test_cutover_batch_runs_idempotently(db):
    m = service.LegacyObjectMappingService
    # 2 valid mappings of TEST_CASE + 1 broken (no canonical target).
    m.upsert(db, 1, {"legacy_type": "TEST_CASE", "legacy_id": 10, "canonical_type": "SCENARIO", "canonical_id": 1})
    m.upsert(db, 1, {"legacy_type": "TEST_CASE", "legacy_id": 11, "canonical_type": "SCENARIO", "canonical_id": 2})
    m.upsert(db, 1, {"legacy_type": "TEST_CASE", "legacy_id": 12, "canonical_type": "", "canonical_id": 0})

    cut = service.LegacyCutoverService
    batch = cut.create_batch(db, {"batch_key": "tc-wave1", "object_type": "TEST_CASE", "project_id": 1})
    result = cut.run_batch(db, batch["id"])
    assert result["status"] == "PARTIAL"
    assert result["planned_count"] == 3
    assert result["migrated_count"] == 2
    assert result["failed_count"] == 1

    # Re-running is idempotent: counters reflect the deterministic final state
    # (2 verified + 1 failed), never double-counted against the batch row.
    rerun = cut.run_batch(db, batch["id"])
    assert rerun["migrated_count"] == 2
    assert rerun["failed_count"] == 1
    assert rerun["status"] == "PARTIAL"
    assert db.query(LegacyObjectMapping).count() == 3


def test_cutover_batch_all_verified_completes(db):
    m = service.LegacyObjectMappingService
    m.upsert(db, 1, {"legacy_type": "DATASET", "legacy_id": 20, "canonical_type": "DATA_SOURCE", "canonical_id": 5})
    cut = service.LegacyCutoverService
    batch = cut.create_batch(db, {"batch_key": "ds-wave1", "object_type": "DATASET", "project_id": 1})
    result = cut.run_batch(db, batch["id"])
    assert result["status"] == "COMPLETED"
    assert result["migrated_count"] == 1
    assert result["failed_count"] == 0


def test_batch_not_found_raises(db):
    with pytest.raises(ValueError):
        service.LegacyCutoverService.run_batch(db, 9999)
