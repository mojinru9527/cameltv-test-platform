"""D 级收敛 API（B14）—— 归档 TestPlan / 资产视图 / 数据资产合并。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import audit_service, convergence_service

router = APIRouter(prefix="/convergence", tags=["D级收敛"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db, user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


@router.get("/assets", response_model=R[dict], summary="单一事实源资产视图")
def assets(
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    return R.ok(convergence_service.unified_assets_view(db, current.project_id or 0))


@router.get("/data-assets", response_model=R[dict], summary="数据资产合并视图（Dataset/Fixtures）")
def data_assets(
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    return R.ok(convergence_service.merged_data_assets(db, current.project_id or 0))


@router.post("/test-plan/{test_plan_id}/archive", response_model=R[dict], summary="TestPlan 只读归档到 VersionTask")
def archive_test_plan(
    test_plan_id: int,
    req: Request,
    version_task_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    result = convergence_service.archive_test_plan(db, test_plan_id, version_task_id)
    _audit(req, current, db, "convergence:archive_test_plan", f"{test_plan_id}", f"task:{version_task_id}")
    return R.ok(result)
