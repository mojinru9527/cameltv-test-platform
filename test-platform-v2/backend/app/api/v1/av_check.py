"""AV check API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.av_check import AvCheckTaskCreate, AvCheckTaskOut, AvCheckTaskUpdate
from app.schemas.common import R
from app.services import av_check_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/av-checks", tags=["音视频专项"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db, user_id=cu.user.id, username=cu.user.username or "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


@router.get("", response_model=R[dict])
def list_tasks(
    protocol: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("avcheck:list")),
    db: Session = Depends(get_db),
):
    items, total = av_check_service.list_tasks(
        db, project_id=current.project_id or 0,
        protocol=protocol, status=status, keyword=keyword, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[AvCheckTaskOut])
def create_task(
    req: Request, body: AvCheckTaskCreate,
    current: CurrentUser = Depends(require_permission("avcheck:create")),
    db: Session = Depends(get_db),
):
    r = av_check_service.create_task(db, body, current.user.id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "avcheck:create", f"#{r['id']} {r['name']}")
    return R.ok(AvCheckTaskOut(**r))


@router.get("/{task_id}", response_model=R[AvCheckTaskOut])
def get_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("avcheck:detail")),
    db: Session = Depends(get_db),
):
    r = av_check_service.get_task(db, task_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("专项测试任务")
    return R.ok(AvCheckTaskOut(**r))


@router.delete("/{task_id}", response_model=R[dict])
def delete_task(
    req: Request, task_id: int,
    current: CurrentUser = Depends(require_permission("avcheck:delete")),
    db: Session = Depends(get_db),
):
    ok = av_check_service.delete_task(db, task_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("专项测试任务")
    db.commit()
    _audit(req, current, db, "avcheck:delete", f"task #{task_id}")
    return R.ok({"deleted": True})


@router.post("/{task_id}/trigger", response_model=R[AvCheckTaskOut])
def trigger_task(
    req: Request, task_id: int,
    current: CurrentUser = Depends(require_permission("avcheck:trigger")),
    db: Session = Depends(get_db),
):
    try:
        r = av_check_service.trigger_check(db, task_id, current.project_id or 0)
        db.commit()
        _audit(req, current, db, "avcheck:trigger", f"#{task_id}")
        return R.ok(AvCheckTaskOut(**r))
    except ValueError as e:
        from app.core.exceptions import APIException
        raise APIException(str(e))


@router.get("/{task_id}/metrics", response_model=R[list])
def get_metrics(
    task_id: int,
    current: CurrentUser = Depends(require_permission("avcheck:detail")),
    db: Session = Depends(get_db),
):
    items = av_check_service.get_metrics(db, task_id, current.project_id or 0)
    return R.ok(items)
