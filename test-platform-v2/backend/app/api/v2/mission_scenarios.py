"""AITDE v2 Scenario API (V30-066..V30-070)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.scenario import service
from app.modules.aitde.scenario.schemas import (
    OracleBindingCreate,
    OracleReviewRequest,
    ScenarioReviewRequest,
)
from app.schemas.common import R

generate_router = APIRouter(
    prefix="/contracts/{contract_version_id}/scenarios",
    tags=["AITDE - Scenario"],
    dependencies=[Depends(require_aitde_v3)],
)
list_router = APIRouter(
    prefix="/missions/{mission_id}/scenarios",
    tags=["AITDE - Scenario"],
    dependencies=[Depends(require_aitde_v3)],
)
scenario_router = APIRouter(
    prefix="/scenarios/{scenario_id}",
    tags=["AITDE - Scenario"],
    dependencies=[Depends(require_aitde_v3)],
)
oracle_router = APIRouter(
    prefix="/oracles/{oracle_id}",
    tags=["AITDE - Scenario"],
    dependencies=[Depends(require_aitde_v3)],
)


@generate_router.post("/generate", response_model=R[dict])
def generate_scenarios(
    contract_version_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    result = service.generate(
        db, contract_version_id, current.project_id or 0, current.user.id
    )
    from app.modules.aitde.contract.models import TestContract, TestContractVersion
    from app.modules.aitde.intelligence.runner import latest_operation_id

    _version = db.get(TestContractVersion, contract_version_id)
    _mission_id = (
        db.get(TestContract, _version.contract_id).mission_id if _version else 0
    )
    result["operation_id"] = latest_operation_id(
        db, _mission_id, current.project_id or 0, "scenario:design"
    )
    return R.ok(result)


@list_router.get("", response_model=R[list])
def list_scenarios(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.list_scenarios(db, mission_id, current.project_id or 0))


@scenario_router.get("", response_model=R[dict])
def get_scenario(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.get_scenario(db, scenario_id, current.project_id or 0))


@scenario_router.post("/review", response_model=R[dict])
def review_scenario(
    scenario_id: int,
    payload: ScenarioReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.review_scenario(
            db, scenario_id, current.project_id or 0, current.user.id, payload
        )
    )


@scenario_router.get("/functional-projection", response_model=R[dict])
def functional_projection(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.functional_projection(
            db, scenario_id, current.project_id or 0
        ).model_dump()
    )


@scenario_router.post("/oracle-bindings", response_model=R[dict])
def create_oracle_binding(
    scenario_id: int,
    payload: OracleBindingCreate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.create_oracle_binding(
            db, scenario_id, current.project_id or 0, payload
        )
    )


@scenario_router.get("/oracle-bindings", response_model=R[list])
def list_oracle_bindings(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.list_oracle_bindings(db, scenario_id, current.project_id or 0)
    )


@oracle_router.post("/review", response_model=R[dict])
def review_oracle(
    oracle_id: int,
    payload: OracleReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    return R.ok(service.review_oracle(db, oracle_id, current.user.id, payload))

