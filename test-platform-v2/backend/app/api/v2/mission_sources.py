"""AITDE v2 Mission Source API (V30-025)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.sources import service
from app.modules.aitde.sources.mapper import artifact_to_dict, fragment_to_dict
from app.modules.aitde.sources.schemas import SourceArtifactCreate, SourceParseResult
from app.schemas.common import R

router = APIRouter(
    prefix="/missions/{mission_id}/sources",
    tags=["AITDE - Sources"],
    dependencies=[Depends(require_aitde_v3)],
)

single_router = APIRouter(
    prefix="/sources",
    tags=["AITDE - Sources"],
    dependencies=[Depends(require_aitde_v3)],
)


@single_router.get("/{source_id}", response_model=R[dict])
def get_source(
    source_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    artifact = service.get_source(db, source_id, current.project_id or 0)
    return R.ok(artifact_to_dict(artifact))


@router.post("", response_model=R[dict])
def attach_source(
    mission_id: int,
    payload: SourceArtifactCreate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    artifact = service.attach_source(
        db, payload, mission_id, current.project_id or 0, current.user.id
    )
    return R.ok(artifact_to_dict(artifact))


@router.get("", response_model=R[dict])
def list_sources(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    rows = service.list_sources(db, mission_id)
    return R.ok([artifact_to_dict(a) for a in rows])


@router.post("/{source_id}/parse", response_model=R[dict])
def parse_source(
    mission_id: int,
    source_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    result: SourceParseResult = service.parse_source(
        db, source_id, current.project_id or 0
    )
    return R.ok(result.model_dump())


@router.get("/{source_id}/fragments", response_model=R[dict])
def source_fragments(
    mission_id: int,
    source_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    rows = service.fragments(db, source_id, current.project_id or 0)
    return R.ok([fragment_to_dict(f) for f in rows])
