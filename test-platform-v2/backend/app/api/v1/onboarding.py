"""新业务接入 API（B15）—— /api/v1/onboarding。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import audit_service, onboarding_service

router = APIRouter(prefix="/onboarding", tags=["新业务接入"])


class OnboardingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    service_key: str = Field(..., min_length=1, max_length=120)
    api_spec_url: str = ""
    base_url: str = ""


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    audit_service.write_audit(
        db, user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _out(ob) -> dict:
    return {
        "id": ob.id, "name": ob.name, "service_key": ob.service_key,
        "status": ob.status, "step": ob.step, "version_task_id": ob.version_task_id,
        "api_spec_url": ob.api_spec_url, "base_url": ob.base_url,
        "baseline": ob.baseline,
    }


@router.post("/businesses", response_model=R[dict], summary="登记新业务（第 1 步）")
def create(
    data: OnboardingCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:create")),
    db: Session = Depends(get_db),
):
    ob = onboarding_service.create_onboarding(
        db, current.project_id or 0, name=data.name, service_key=data.service_key,
        api_spec_url=data.api_spec_url, base_url=data.base_url,
    )
    _audit(req, current, db, "onboarding:create", f"{ob.id}", ob.name)
    return R.ok(_out(ob))


@router.get("/businesses", response_model=R[list[dict]], summary="接入列表")
def list_all(
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    return R.ok([_out(ob) for ob in onboarding_service.list_onboardings(db, current.project_id or 0)])


@router.post("/businesses/{onboarding_id}/steps/{step}", response_model=R[dict], summary="推进接入步骤")
def complete_step(
    onboarding_id: int,
    step: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    ob = onboarding_service.complete_step(db, onboarding_id, step)
    _audit(req, current, db, "onboarding:step", f"{ob.id}", f"step:{step}")
    return R.ok(_out(ob))
