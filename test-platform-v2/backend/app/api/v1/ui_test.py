"""UI test API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import R
from app.schemas.ui_test import UiTestJobCreate, UiTestJobDetailOut, UiTestJobOut, UiTestJobUpdate, UiTestRunOut
from app.services import ui_test_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/ui-tests", tags=["UI 自动化"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db, user_id=cu.user.id, username=cu.user.username or "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


@router.get("", response_model=R[dict])
def list_jobs(
    status: str | None = Query(None),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
):
    items, total = ui_test_service.list_jobs(
        db, project_id=current.project_id or 0,
        status=status, keyword=keyword, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[UiTestJobOut])
def create_job(
    req: Request, body: UiTestJobCreate,
    current: CurrentUser = Depends(require_permission("uitest:create")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.create_job(db, body, current.user.id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "uitest:create", f"#{r['id']} {r['name']}")
    return R.ok(UiTestJobOut(**r))


@router.get("/{job_id}", response_model=R[UiTestJobDetailOut])
def get_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.get_job(db, job_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    return R.ok(UiTestJobDetailOut(**r))


@router.put("/{job_id}", response_model=R[UiTestJobOut])
def update_job(
    req: Request, job_id: int, body: UiTestJobUpdate,
    current: CurrentUser = Depends(require_permission("uitest:update")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.update_job(db, job_id, body, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    db.commit()
    _audit(req, current, db, "uitest:update", f"#{job_id}")
    return R.ok(UiTestJobOut(**r))


@router.delete("/{job_id}", response_model=R[dict])
def delete_job(
    req: Request, job_id: int,
    current: CurrentUser = Depends(require_permission("uitest:delete")),
    db: Session = Depends(get_db),
):
    ok = ui_test_service.delete_job(db, job_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    db.commit()
    _audit(req, current, db, "uitest:delete", f"job #{job_id}")
    return R.ok({"deleted": True})


@router.post("/{job_id}/trigger", response_model=R[UiTestRunOut])
def trigger_job(
    req: Request, job_id: int,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
):
    try:
        r = ui_test_service.trigger_job(db, job_id, current.project_id or 0)
        db.commit()
        _audit(req, current, db, "uitest:trigger", f"#{job_id}")
        return R.ok(UiTestRunOut(**r))
    except ValueError as e:
        from app.core.exceptions import APIException
        raise APIException(str(e))


@router.get("/{job_id}/runs", response_model=R[dict])
def get_runs(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    items, total = ui_test_service.list_runs(
        db, job_id, current.project_id or 0, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})
