"""AITDE v2 Scenario Adapter API (V31-001).

Create / list the adapter that binds a ScenarioVersion to an existing API/UI
asset or a future Runtime Adapter. Mounted under ``/api/v2``, feature-gated.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.execution import adapter_registry
from app.modules.aitde.execution.mapper import adapter_to_dict
from app.modules.aitde.execution.schemas import AdapterCreate, AdapterUpdate
from app.schemas.common import R

router = APIRouter(
    prefix="/scenarios",
    tags=["AITDE - Scenario Adapters"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/{scenario_id}/adapters", response_model=R[dict])
def create_adapter(
    scenario_id: int,
    payload: AdapterCreate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = adapter_registry.create_adapter(
        db,
        scenario_id,
        payload.model_dump(),
        project_id=current.project_id or 0,
        user_id=current.user.id,
    )
    return R.ok(adapter_to_dict(row))


@router.get("/{scenario_id}/adapters", response_model=R[dict])
def list_adapters(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    items = adapter_registry.list_adapters(db, scenario_id, current.project_id or 0)
    return R.ok({"items": [adapter_to_dict(a) for a in items]})


@router.patch("/adapters/{adapter_id}", response_model=R[dict])
def update_adapter(
    adapter_id: int,
    payload: AdapterUpdate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = adapter_registry.update_adapter(
        db, adapter_id, current.project_id or 0, payload.model_dump(exclude_unset=True)
    )
    return R.ok(adapter_to_dict(row))
