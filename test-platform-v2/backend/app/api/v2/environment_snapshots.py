"""AITDE v2 Environment Snapshot API (V31-001/V31-005).

Capture an EnvironmentSnapshot for a given environment (and optionally mission).
Every ExecutionRun binds one snapshot so the run's environment identity is
reproducible. Mounted under ``/api/v2``, feature-gated.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.modules.aitde.environment import snapshot_service
from app.modules.aitde.environment.snapshot_service import latest_snapshot
from app.modules.aitde.execution.mapper import snapshot_to_dict
from app.modules.aitde.execution.schemas import EnvironmentSnapshotCreate
from app.schemas.common import R

router = APIRouter(
    prefix="/environments",
    tags=["AITDE - Environment Snapshots"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/{environment_id}/snapshots", response_model=R[dict])
def create_snapshot(
    environment_id: int,
    payload: EnvironmentSnapshotCreate,
    mission_id: int = Query(..., description="Mission the snapshot belongs to"),
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = snapshot_service.capture_snapshot(
        db,
        environment_id=environment_id,
        mission_id=mission_id,
        project_id=current.project_id or 0,
        data=payload.model_dump(),
    )
    return R.ok(snapshot_to_dict(row))


@router.get("/{environment_id}/snapshots/latest", response_model=R[dict])
def get_latest_snapshot(
    environment_id: int,
    mission_id: int = Query(..., description="Mission the snapshot belongs to"),
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    row = latest_snapshot(db, environment_id, mission_id)
    if not row:
        raise APIException(code=404, msg="尚未捕获环境快照", http_status=404)
    return R.ok(snapshot_to_dict(row))
