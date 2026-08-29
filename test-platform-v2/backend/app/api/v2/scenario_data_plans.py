"""AITDE v2 Data Plan API (V32-003).

The planner declares a strategy + steps (never executes). High-risk plans
require approval before execution.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.data import service
from app.modules.aitde.data.schemas import DataPlanGenerateRequest
from app.schemas.common import R

scenario_plan_router = APIRouter(
    prefix="/scenarios/{scenario_version_id}/data-plans",
    tags=["AITDE - Data Plans"],
    dependencies=[Depends(require_aitde_v3)],
)

data_plan_router = APIRouter(
    prefix="/data-plans",
    tags=["AITDE - Data Plans"],
    dependencies=[Depends(require_aitde_v3)],
)


@scenario_plan_router.post("", response_model=R[dict])
def generate_data_plan(
    scenario_version_id: int,
    payload: DataPlanGenerateRequest,
    current: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    plan = service.generate_data_plan(
        db,
        scenario_version_id,
        payload.environment_id,
        current.project_id or 0,
        payload,
    )
    return R.ok(service.to_plan_dict(db, plan))


@data_plan_router.get("/{plan_id}", response_model=R[dict])
def get_data_plan(
    plan_id: int,
    _: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    plan = service.get_data_plan(db, plan_id)
    return R.ok(service.to_plan_dict(db, plan))


@data_plan_router.post("/{plan_id}/approve", response_model=R[dict])
def approve_data_plan(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    plan = service.approve_data_plan(db, plan_id, current.user.id)
    return R.ok(service.to_plan_dict(db, plan))
