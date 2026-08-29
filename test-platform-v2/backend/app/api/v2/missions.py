"""AITDE v2 Mission API (V30-013).

Reuses the platform's ``require_permission`` + ``X-Project-Id`` scoping and the
``R`` envelope. Mounted under ``/api/v2``. Business endpoints are feature-gated
via ``require_aitde_v3`` (V30-001).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.mission import service
from app.modules.aitde.mission.mapper import mission_to_dict
from app.modules.aitde.mission.schemas import MissionCreate, MissionUpdate
from app.schemas.common import R

router = APIRouter(
    prefix="/missions",
    tags=["AITDE - Missions"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("", response_model=R[dict])
def create_mission(
    payload: MissionCreate,
    current: CurrentUser = Depends(require_permission("mission:create")),
    db: Session = Depends(get_db),
):
    mission = service.create_mission(
        db,
        payload.model_dump(),
        project_id=current.project_id or 0,
        user_id=current.user.id,
    )
    return R.ok(mission_to_dict(mission))


@router.get("", response_model=R[dict])
def list_missions(
    status: str = Query(""),
    mission_type: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    items, total = service.list_missions(
        db,
        current.project_id or 0,
        status=status,
        mission_type=mission_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [mission_to_dict(m) for m in items],
        }
    )


@router.get("/{mission_id}", response_model=R[dict])
def get_mission(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    mission = service.get_mission(db, mission_id, current.project_id or 0)
    return R.ok(mission_to_dict(mission))


@router.patch("/{mission_id}", response_model=R[dict])
def update_mission(
    mission_id: int,
    payload: MissionUpdate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    mission = service.update_mission(
        db,
        mission_id,
        current.project_id or 0,
        payload.model_dump(exclude_unset=True),
    )
    return R.ok(mission_to_dict(mission))


@router.post("/{mission_id}/archive", response_model=R[dict])
def archive_mission(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    mission = service.archive_mission(db, mission_id, current.project_id or 0)
    return R.ok(mission_to_dict(mission))
