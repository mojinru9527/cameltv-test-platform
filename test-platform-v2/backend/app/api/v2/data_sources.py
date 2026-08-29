"""AITDE v2 Data Source API (V32-001).

Project-scoped typed data sources. Creating against a production environment is
restricted to READONLY by the service; the secret value is never returned.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.data import service
from app.modules.aitde.data.schemas import DataSourceCreate
from app.schemas.common import R

router = APIRouter(
    prefix="/data-sources",
    tags=["AITDE - Data Sources"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.get("", response_model=R[list])
def list_data_sources(
    current: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    rows = service.list_data_sources(db, current.project_id or 0)
    return R.ok([service.to_dict(r) for r in rows])


@router.post("", response_model=R[dict])
def create_data_source(
    payload: DataSourceCreate,
    current: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    row = service.create_data_source(
        db, payload, current.project_id or 0, current.user.id
    )
    return R.ok(service.to_dict(row))


@router.get("/{data_source_id}", response_model=R[dict])
def get_data_source(
    data_source_id: int,
    current: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    row = service.get_data_source(db, data_source_id, current.project_id or 0)
    return R.ok(service.to_dict(row))


@router.post("/{data_source_id}/test", response_model=R[dict])
def test_data_source_connection(
    data_source_id: int,
    current: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    result = service.test_data_source_connection(
        db, data_source_id, current.project_id or 0
    )
    return R.ok(result)
