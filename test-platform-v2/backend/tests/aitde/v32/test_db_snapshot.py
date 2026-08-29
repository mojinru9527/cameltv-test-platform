"""DB snapshot tests (V32-011)."""
from __future__ import annotations

from app.modules.aitde.data import snapshot_service


def test_snapshot_content_hash_stable(db):
    s1 = snapshot_service.capture_snapshot(
        db, fixture_id=1, run_id=2, entity_id=3, snapshot_type="BEFORE",
        snapshot_json={"status": "active"},
    )
    s2 = snapshot_service.capture_snapshot(
        db, fixture_id=1, run_id=2, entity_id=3, snapshot_type="BEFORE",
        snapshot_json={"status": "active"},
    )
    assert s1.content_hash == s2.content_hash
    assert snapshot_service.to_snapshot_dict(s1)["snapshot_type"] == "BEFORE"


def test_snapshot_different_content_different_hash(db):
    s1 = snapshot_service.capture_snapshot(
        db, fixture_id=1, run_id=2, entity_id=3, snapshot_type="AFTER",
        snapshot_json={"status": "active"},
    )
    s2 = snapshot_service.capture_snapshot(
        db, fixture_id=1, run_id=2, entity_id=3, snapshot_type="AFTER",
        snapshot_json={"status": "expired"},
    )
    assert s1.content_hash != s2.content_hash


def test_snapshot_listing(db):
    snapshot_service.capture_snapshot(
        db, fixture_id=9, run_id=1, entity_id=None, snapshot_type="CLEANUP_VERIFY",
        snapshot_json={"clean": True},
    )
    rows = snapshot_service.list_snapshots(db, 9)
    assert len(rows) == 1
    assert rows[0].fixture_id == 9
