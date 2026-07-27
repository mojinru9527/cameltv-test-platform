"""Schedule API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db, require_permission
from app.schemas.common import R
from app.schemas.test_schedule import (
    ScheduleCreate,
    ScheduleOut,
    ScheduleRunOut,
    ScheduleUpdate,
)
from app.services import schedule_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/schedules", tags=["定时任务"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username or "",
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )


@router.get("", response_model=R[dict])
def list_schedules(
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("schedule:list")),
    db: Session = Depends(get_db),
):
    items, total = schedule_service.list_schedules(
        db,
        project_id=current.project_id or 0,
        enabled=enabled,
        page=page,
        page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[ScheduleOut])
def create_schedule(
    req: Request,
    body: ScheduleCreate,
    current: CurrentUser = Depends(require_permission("schedule:create")),
    db: Session = Depends(get_db),
):
    try:
        r = schedule_service.create_schedule(db, body, current.user.id, current.project_id or 0)
        db.commit()
        _audit(req, current, db, "schedule:create", f"#{r['id']} {r['name']}")
        return R.ok(ScheduleOut(**r))
    except ValueError as e:
        from app.core.exceptions import APIException
        raise APIException(str(e))


@router.get("/{schedule_id}", response_model=R[ScheduleOut])
def get_schedule(
    schedule_id: int,
    current: CurrentUser = Depends(require_permission("schedule:list")),
    db: Session = Depends(get_db),
):
    r = schedule_service.get_schedule(db, schedule_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("调度")
    return R.ok(ScheduleOut(**r))


@router.put("/{schedule_id}", response_model=R[ScheduleOut])
def update_schedule(
    req: Request,
    schedule_id: int,
    body: ScheduleUpdate,
    current: CurrentUser = Depends(require_permission("schedule:update")),
    db: Session = Depends(get_db),
):
    r = schedule_service.update_schedule(db, schedule_id, body, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("调度")
    db.commit()
    _audit(req, current, db, "schedule:update", f"#{schedule_id}")
    return R.ok(ScheduleOut(**r))


@router.delete("/{schedule_id}", response_model=R[dict])
def delete_schedule(
    req: Request,
    schedule_id: int,
    current: CurrentUser = Depends(require_permission("schedule:delete")),
    db: Session = Depends(get_db),
):
    ok = schedule_service.delete_schedule(db, schedule_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("调度")
    db.commit()
    _audit(req, current, db, "schedule:delete", f"schedule #{schedule_id}")
    return R.ok({"deleted": True})


@router.post("/{schedule_id}/trigger", response_model=R[dict])
def trigger_schedule(
    req: Request,
    schedule_id: int,
    current: CurrentUser = Depends(require_permission("schedule:trigger")),
    db: Session = Depends(get_db),
):
    try:
        r = schedule_service.trigger_schedule(db, schedule_id, current.project_id or 0)
        _audit(req, current, db, "schedule:trigger", f"#{schedule_id}")
        return R.ok(r)
    except ValueError as e:
        from app.core.exceptions import APIException
        raise APIException(str(e))


@router.get("/{schedule_id}/runs", response_model=R[dict])
def get_schedule_runs(
    schedule_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("schedule:list")),
    db: Session = Depends(get_db),
):
    items, total = schedule_service.get_runs(
        db, schedule_id, current.project_id or 0, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})
