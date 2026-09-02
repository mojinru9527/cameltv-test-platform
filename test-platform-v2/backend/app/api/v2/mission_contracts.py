"""AITDE v2 Contract API (V30-056)."""

from __future__ import annotations


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.contract import service
from app.modules.aitde.contract.models import TestContract
from app.modules.aitde.contract.schemas import (
    ContractFreezeRequest,
    ContractGenerateRequest,
)
from app.schemas.common import R

router = APIRouter(
    prefix="/missions/{mission_id}",
    tags=["AITDE - Contract"],
    dependencies=[Depends(require_aitde_v3)],
)
contracts_router = APIRouter(
    prefix="/contracts/{contract_id}",
    tags=["AITDE - Contract"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/contracts/generate", response_model=R[dict])
def generate_contract(
    mission_id: int,
    payload: ContractGenerateRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    result = service.generate(
        db, mission_id, current.project_id or 0, current.user.id, payload
    )
    from app.modules.aitde.intelligence.runner import latest_operation_id

    result["operation_id"] = latest_operation_id(
        db, mission_id, current.project_id or 0, "contract:build"
    )
    return R.ok(result)


@router.get("/contract", response_model=R[dict])
def get_current_contract(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    result = service.get_current(db, mission_id)
    return R.ok(result)


@contracts_router.get("/versions", response_model=R[dict])
def list_versions(
    contract_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.list_versions(db, contract_id))


@contracts_router.post("/freeze", response_model=R[dict])
def freeze_contract(
    contract_id: int,
    payload: ContractFreezeRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    contract = db.get(TestContract, contract_id)
    if not contract:
        return R.err(code=404, msg="Contract 不存在")
    result = service.freeze(
        db,
        contract_id,
        contract.mission_id,
        current.project_id or 0,
        current.user.id,
        payload,
    )
    return R.ok(result)


@contracts_router.post("/change-proposals", response_model=R[dict])
def create_change_proposal(
    contract_id: int,
    payload: dict,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    contract = db.get(TestContract, contract_id)
    if not contract:
        return R.err(code=404, msg="Contract 不存在")
    return R.ok(
        service.create_change_proposal(
            db, contract.mission_id, current.project_id or 0, current.user.id, payload
        )
    )


@contracts_router.get("/diff", response_model=R[dict])
def contract_diff(
    contract_id: int,
    base: int = Query(..., ge=1),
    target: int = Query(..., ge=1),
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.diff(db, contract_id, base, target).model_dump())

