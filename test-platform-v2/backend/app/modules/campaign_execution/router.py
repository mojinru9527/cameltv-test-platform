from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.modules.campaign_execution.service import start_campaign

router = APIRouter(prefix="/execution", tags=["统一执行"])


@router.post("/campaigns/{campaign_id}/runs", response_model=R[dict])
def run_campaign(
    campaign_id: int,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    runs = start_campaign(db, project_id=current.project_id, campaign_id=campaign_id, user_id=current.user.id)
    return R.ok({"campaign_id": campaign_id, "run_ids": [r.id for r in runs]})
