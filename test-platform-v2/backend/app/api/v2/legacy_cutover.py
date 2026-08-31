"""AITDE v2 Legacy Cutover API (V40).

Legacy usage inventory (V40-001) + legacy mapping / cutover batch (V40-002).
Mounted under ``/api/v2`` and feature-gated. The v1 surfaces these records are
retiring stay untouched; this API only observes and maps.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.legacy_cutover import service
from app.modules.aitde.legacy_cutover.schemas import (
    CutoverBatchIn,
    MappingUpsertIn,
    UsageRecordIn,
)
from app.schemas.common import R

router = APIRouter(
    tags=["AITDE - Legacy Cutover"], dependencies=[Depends(require_aitde_v3)]
)


def _issue_404(msg: str) -> NoReturn:
    from app.core.exceptions import APIException

    raise APIException(code=404, msg=msg, http_status=404)


# ── Legacy Usage Inventory (V40-001) ─────────────────────────────────────────


@router.post("/legacy/usage/record", response_model=R[dict])
def record_usage(
    payload: UsageRecordIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.LegacyUsageInventoryService.record(
            db, current.project_id or 0, payload.model_dump()
        )
    )


@router.get("/legacy/usage", response_model=R[list[dict]])
def list_usage(
    object_type: str | None = None,
    stage: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.LegacyUsageInventoryService.query(
            db,
            current.project_id or 0,
            object_type=object_type,
            stage=stage,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/legacy/usage/unknown", response_model=R[list[dict]])
def unknown_consumers(
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    """V40-001 verification: list consumers not yet classified."""
    return R.ok(
        service.LegacyUsageInventoryService.unknown_consumers(
            db, current.project_id or 0
        )
    )


# ── Legacy Mapping / Cutover Batch (V40-002) ────────────────────────────────


@router.post("/legacy/mappings", response_model=R[dict])
def upsert_mapping(
    payload: MappingUpsertIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.LegacyObjectMappingService.upsert(
            db, current.project_id or 0, payload.model_dump()
        )
    )


@router.get("/legacy/mappings", response_model=R[list[dict]])
def list_mappings(
    object_type: str | None = None,
    limit: int = 200,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.LegacyObjectMappingService.list(
            db, current.project_id or 0, object_type=object_type, limit=limit
        )
    )


@router.post("/legacy/mappings/{mapping_id}/verify", response_model=R[dict])
def verify_mapping(
    mapping_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = service.LegacyObjectMappingService.verify(db, mapping_id)
    if data is None:
        _issue_404("mapping 不存在")
    return R.ok(data)


@router.post("/legacy/cutover-batches", response_model=R[dict])
def create_batch(
    payload: CutoverBatchIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    plan = payload.model_dump()
    plan["project_id"] = current.project_id or 0
    return R.ok(service.LegacyCutoverService.create_batch(db, plan))


@router.get("/legacy/cutover-batches/{batch_id}", response_model=R[dict])
def get_batch(
    batch_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = service.LegacyCutoverService.get_batch(db, batch_id)
    if data is None:
        _issue_404("batch 不存在")
    return R.ok(data)


@router.post("/legacy/cutover-batches/{batch_id}/run", response_model=R[dict])
def run_batch(
    batch_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    try:
        data = service.LegacyCutoverService.run_batch(db, batch_id)
    except ValueError as exc:
        _issue_404(str(exc))
    return R.ok(data)
