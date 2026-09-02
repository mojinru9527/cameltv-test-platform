"""运营指标 API（B13）—— /api/v1/metrics/operations。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import version_task_service

router = APIRouter(prefix="/metrics", tags=["运营指标"])


@router.get("/operations", response_model=R[dict], summary="运营指标看板")
def operations_metrics(
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    return R.ok(version_task_service.get_operations_metrics(db, current.project_id or 0))
