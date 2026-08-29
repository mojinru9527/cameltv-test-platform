"""DataSnapshotService (V32-011): before/after/verify snapshots with a content hash.

Snapshots feed into V3.2 evidence (FIXTURE_MANIFEST / DB_BEFORE / DB_AFTER /
DB_CLEANUP_VERIFY) downstream.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.modules.aitde.data import repository
from app.modules.aitde.data.models import DataSnapshot


def capture_snapshot(
    db: Session,
    fixture_id: int,
    run_id: int | None,
    entity_id: int | None,
    snapshot_type: str,
    snapshot_json: Any,
) -> DataSnapshot:
    payload = json.dumps(snapshot_json, ensure_ascii=False, sort_keys=True)
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    snap = repository.create_snapshot(
        db,
        {
            "fixture_id": fixture_id,
            "run_id": run_id,
            "entity_id": entity_id,
            "snapshot_type": snapshot_type,
            "snapshot_json": payload,
            "content_hash": content_hash,
        },
    )
    db.commit()
    db.refresh(snap)
    return snap


def to_snapshot_dict(snap: DataSnapshot) -> dict[str, Any]:
    return {
        "id": snap.id,
        "fixture_id": snap.fixture_id,
        "run_id": snap.run_id,
        "entity_id": snap.entity_id,
        "snapshot_type": snap.snapshot_type,
        "storage_uri": snap.storage_uri,
        "snapshot_json": snap.snapshot_json,
        "content_hash": snap.content_hash,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
    }


def list_snapshots(db: Session, fixture_id: int) -> list[DataSnapshot]:
    return repository.list_snapshots(db, fixture_id)
