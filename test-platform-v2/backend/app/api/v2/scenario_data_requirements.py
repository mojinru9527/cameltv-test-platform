"""AITDE v2 Data Requirement API (V32-002).

Data requirements are the business data needs of a scenario (Given/Expected
state), never SQL. Derivation is rule-based in V32-002; testers may revise.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.data import service
from app.modules.aitde.data.schemas import (
    DataRequirementDeriveRequest,
    DataRequirementUpdate,
)
from app.schemas.common import R

scenario_data_router = APIRouter(
    prefix="/scenarios/{scenario_version_id}/data-requirements",
    tags=["AITDE - Data Requirements"],
    dependencies=[Depends(require_aitde_v3)],
)

data_requirement_router = APIRouter(
    prefix="/data-requirements",
    tags=["AITDE - Data Requirements"],
    dependencies=[Depends(require_aitde_v3)],
)


@scenario_data_router.get("", response_model=R[dict])
def list_data_requirements(
    scenario_version_id: int,
    _: CurrentUser = Depends(require_permission("data_source:list")),
    db: Session = Depends(get_db),
):
    rows = service.list_data_requirements(db, scenario_version_id)
    return R.ok([service.to_requirement_dict(r) for r in rows])


@scenario_data_router.post("/derive", response_model=R[dict])
def derive_data_requirements(
    scenario_version_id: int,
    _payload: DataRequirementDeriveRequest,
    _: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    rows = service.derive_data_requirements(db, scenario_version_id)
    return R.ok([service.to_requirement_dict(r) for r in rows])


@data_requirement_router.patch("/{requirement_id}", response_model=R[dict])
def update_data_requirement(
    requirement_id: int,
    payload: DataRequirementUpdate,
    _: CurrentUser = Depends(require_permission("data_source:manage")),
    db: Session = Depends(get_db),
):
    row = service.update_data_requirement(db, requirement_id, payload)
    return R.ok(service.to_requirement_dict(row))
