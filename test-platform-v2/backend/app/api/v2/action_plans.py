"""AITDE v2 Action Plan API (PR33-01).

Command IR + CommandPlan versioning surface: generate a draft version, list
versions, validate IR, approve. Permission-gated + AITDE V3 enabled.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.command import DEFAULT_REGISTRY, service
from app.schemas.common import R

router = APIRouter(
    prefix="/scenarios/{scenario_id}/action-plans",
    tags=["AITDE - Action Plans"],
    dependencies=[Depends(require_aitde_v3)],
)

plans_router = APIRouter(
    prefix="/action-plans",
    tags=["AITDE - Action Plans"],
    dependencies=[Depends(require_aitde_v3)],
)


class ActionPlanGenerateRequest(BaseModel):
    scenario_version_id: int
    contract_version_id: int
    plan: dict | None = Field(
        default=None,
        description=(
            "Command IR document. Omit to let the server derive a DRAFT "
            "from the scenario (ActionPlanner)."
        ),
    )
    schema_version: str = "1.0"
    model_ref: str | None = None
    prompt_version: str | None = None


@router.post("/generate", response_model=R[dict])
def generate_action_plan(
    scenario_id: int,
    payload: ActionPlanGenerateRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    # V33-002: key the plan by scenario_id as the scenario_adapter proxy (adapter
    # binding is V33-003+). Batch 207: when no plan is supplied the server
    # derives a DRAFT from the scenario (ActionPlanner) so the client never has
    # to hand-write Command IR.
    plan = service.get_or_create_plan(db, scenario_id)
    if payload.plan is None:
        ir = service.plan_from_scenario(
            db, payload.scenario_version_id, route="/"
        )
        generated_by_type = "PLANNER"
    else:
        ir = payload.plan
        generated_by_type = "CLIENT"
    version = service.create_version(
        db,
        plan,
        scenario_version_id=payload.scenario_version_id,
        contract_version_id=payload.contract_version_id,
        plan_json=ir,
        schema_version=payload.schema_version,
        generated_by_type=generated_by_type,
        model_ref=payload.model_ref,
        prompt_version=payload.prompt_version,
    )
    return R.ok(service.to_version_dict(version))


@router.get("", response_model=R[list])
def list_action_plans(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    plan = service.get_or_create_plan(db, scenario_id)
    versions = service.list_versions(db, plan.id)
    return R.ok([service.to_version_dict(v) for v in versions])


@plans_router.post("/{version_id}/validate", response_model=R[dict])
def validate_action_plan(
    version_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    version = service.get_version(db, version_id)
    errors = DEFAULT_REGISTRY.validate(json.loads(version.plan_json or "{}"))
    return R.ok({"valid": not errors, "errors": errors})


@plans_router.post("/{version_id}/approve", response_model=R[dict])
def approve_action_plan(
    version_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    version = service.approve_version(db, version_id, current.user.id)
    return R.ok(service.to_version_dict(version))
