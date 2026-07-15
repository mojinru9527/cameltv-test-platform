"""AV check API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.av_check import (
    AvCheckMeasurementCreate,
    AvCheckMeasurementOut,
    AvCheckMeasurementUpdate,
    AvCheckTaskCreate,
    AvCheckTaskOut,
    AvCheckTaskUpdate,
)
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


@router.get("/templates/measurements", response_model=R[list], summary="音视频测量模板")
def measurement_templates(
    current: CurrentUser = Depends(require_permission("avcheck:list")),
):
    return R.ok(av_check_service.list_measurement_templates())


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


@router.put("/{task_id}", response_model=R[AvCheckTaskOut])
def update_task(
    req: Request,
    task_id: int,
    body: AvCheckTaskUpdate,
    current: CurrentUser = Depends(require_permission("avcheck:create")),
    db: Session = Depends(get_db),
):
    result = av_check_service.update_task(db, task_id, current.project_id or 0, body)
    if not result:
        from app.core.exceptions import not_found
        raise not_found("专项测试任务")
    db.commit()
    _audit(req, current, db, "avcheck:update", f"task #{task_id}")
    return R.ok(AvCheckTaskOut(**result))


@router.post("/{task_id}/measurements", response_model=R[AvCheckMeasurementOut])
def create_measurement(
    req: Request,
    task_id: int,
    body: AvCheckMeasurementCreate,
    current: CurrentUser = Depends(require_permission("avcheck:create")),
    db: Session = Depends(get_db),
):
    try:
        result = av_check_service.create_measurement(
            db, task_id, current.project_id or 0, current.user.id, body,
        )
    except ValueError as exc:
        from app.core.exceptions import APIException
        raise APIException(str(exc))
    db.commit()
    _audit(req, current, db, "avcheck:measurement:create", f"task #{task_id} {body.metric_type}")
    from app.services.notify_service import queue_notification
    queue_notification(
        current.project_id or 0,
        "test_result",
        {
            "task_name": f"音视频专项 #{task_id} - {result['metric_name']}",
            "passed": 1 if result["passed"] else 0,
            "failed": 0 if result["passed"] else 1,
            "skipped": 0,
            "pass_rate": "100%" if result["passed"] else "0%",
            "conclusion": "达标" if result["passed"] else "未达标",
            "link": "/special",
        },
    )
    return R.ok(AvCheckMeasurementOut(**result))


@router.put("/{task_id}/measurements/{measurement_id}", response_model=R[AvCheckMeasurementOut])
def update_measurement(
    req: Request,
    task_id: int,
    measurement_id: int,
    body: AvCheckMeasurementUpdate,
    current: CurrentUser = Depends(require_permission("avcheck:create")),
    db: Session = Depends(get_db),
):
    result = av_check_service.update_measurement(
        db, task_id, measurement_id, current.project_id or 0, body,
    )
    if not result:
        from app.core.exceptions import not_found
        raise not_found("音视频测量记录")
    db.commit()
    _audit(req, current, db, "avcheck:measurement:update", f"measurement #{measurement_id}")
    return R.ok(AvCheckMeasurementOut(**result))


@router.delete("/{task_id}/measurements/{measurement_id}", response_model=R[dict])
def delete_measurement(
    req: Request,
    task_id: int,
    measurement_id: int,
    current: CurrentUser = Depends(require_permission("avcheck:delete")),
    db: Session = Depends(get_db),
):
    if not av_check_service.delete_measurement(
        db, task_id, measurement_id, current.project_id or 0,
    ):
        from app.core.exceptions import not_found
        raise not_found("音视频测量记录")
    db.commit()
    _audit(req, current, db, "avcheck:measurement:delete", f"measurement #{measurement_id}")
    return R.ok({"deleted": True})


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
    from app.services.notify_service import queue_notification

    task_before = av_check_service.get_task(db, task_id, current.project_id or 0)
    queue_notification(
        current.project_id or 0,
        "task_started",
        {
            "task_type": "音视频流探测",
            "task_name": task_before["name"] if task_before else f"专项任务 #{task_id}",
            "triggered_by": current.user.nickname or current.user.username,
            "link": "/special",
        },
    )
    try:
        r = av_check_service.trigger_check(db, task_id, current.project_id or 0)
        db.commit()
        _audit(req, current, db, "avcheck:trigger", f"#{task_id}")
        metric_total = len(r.get("metrics") or [])
        metric_passed = sum(1 for item in (r.get("metrics") or []) if item.get("pass_"))
        queue_notification(
            current.project_id or 0,
            "task_finished",
            {
                "task_type": "音视频流探测",
                "task_name": r["name"],
                "status": r["status"],
                "result_summary": f"达标 {metric_passed} / 总计 {metric_total}",
                "link": "/special",
            },
        )
        queue_notification(
            current.project_id or 0,
            "test_result",
            {
                "task_name": r["name"],
                "passed": metric_passed,
                "failed": max(0, metric_total - metric_passed),
                "skipped": 0,
                "pass_rate": f"{round(metric_passed * 100 / metric_total, 1)}%" if metric_total else "0%",
                "conclusion": "通过" if metric_total and metric_passed == metric_total else "未通过",
                "link": "/special",
            },
        )
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
