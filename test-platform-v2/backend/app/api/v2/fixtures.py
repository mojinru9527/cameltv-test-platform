"""AITDE v2 Fixture API (V32-009..V32-012).

Fixture detail, lease, release, cleanup and snapshot endpoints for the data
runtime UI + execution integration.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.data import (
    cleanup_service,
    fixture_service,
    lease_service,
    snapshot_service,
)
from app.modules.aitde.data.schemas import (
    FixtureLeaseRequest,
    FixtureReleaseRequest,
    SnapshotCaptureRequest,
)
from app.schemas.common import R

router = APIRouter(
    prefix="/fixtures",
    tags=["AITDE - Fixtures"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.get("/{fixture_id}", response_model=R[dict])
def get_fixture(
    fixture_id: int,
    _: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    fixture = fixture_service.get_fixture(db, fixture_id)
    return R.ok(fixture_service.to_fixture_dict(db, fixture))


@router.post("/{fixture_id}/lease", response_model=R[dict])
def lease_fixture(
    fixture_id: int,
    lease: FixtureLeaseRequest,
    _: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    row = lease_service.lease_fixture(db, fixture_id, lease.run_id, lease.ttl_seconds)
    return R.ok(
        {"id": row.id, "fixture_id": row.fixture_id, "run_id": row.run_id, "status": row.status}
    )


@router.post("/{fixture_id}/release", response_model=R[dict])
def release_fixture(
    fixture_id: int,
    payload: FixtureReleaseRequest,
    _: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    row = lease_service.release_lease(db, payload.lease_id)
    return R.ok({"id": row.id, "status": row.status})


@router.post("/{fixture_id}/cleanup", response_model=R[dict])
def cleanup_fixture(
    fixture_id: int,
    _: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    result = cleanup_service.cleanup_fixture(db, fixture_id)
    return R.ok(result)


@router.get("/{fixture_id}/snapshots", response_model=R[dict])
def list_snapshots(
    fixture_id: int,
    _: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    rows = snapshot_service.list_snapshots(db, fixture_id)
    return R.ok([snapshot_service.to_snapshot_dict(s) for s in rows])


@router.post("/{fixture_id}/snapshots", response_model=R[dict])
def capture_snapshot(
    fixture_id: int,
    payload: SnapshotCaptureRequest,
    _: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    snap = snapshot_service.capture_snapshot(
        db,
        fixture_id,
        payload.run_id,
        payload.entity_id,
        payload.snapshot_type,
        payload.snapshot,
    )
    return R.ok(snapshot_service.to_snapshot_dict(snap))
