"""Notification channel management API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission, require_project
from app.schemas.common import R
from app.services import notify_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/notify", tags=["通知配置"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    """P1-6/S3c: 审计日志 — 通知配置操作追溯。"""
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


@router.get("/channels", response_model=R[list], summary="通知渠道列表")
def list_channels(
    current: CurrentUser = Depends(require_permission("notify:list")),
    db: Session = Depends(get_db),
):
    channels = notify_service.list_channels(db, current.project_id)
    return R.ok(channels)


@router.post("/channels", response_model=R[dict], summary="新建通知渠道")
def create_channel(
    body: dict,
    req: Request,
    current: CurrentUser = Depends(require_permission("notify:manage")),
    db: Session = Depends(get_db),
):
    ch = notify_service.create_channel(db, body, current.project_id)
    db.commit()
    _audit(req, current, db, "notify:channel:create", ch.get("name", ""))
    return R.ok(ch)


@router.put("/channels/{ch_id}", response_model=R[dict], summary="更新通知渠道")
def update_channel(
    ch_id: int,
    body: dict,
    req: Request,
    current: CurrentUser = Depends(require_permission("notify:manage")),
    db: Session = Depends(get_db),
):
    ch = notify_service.update_channel(db, ch_id, body, current.project_id)
    if not ch:
        from app.core.exceptions import not_found
        raise not_found("通知渠道")
    db.commit()
    _audit(req, current, db, "notify:channel:update", f"#{ch_id}")
    return R.ok(ch)


@router.delete("/channels/{ch_id}", response_model=R[dict], summary="删除通知渠道")
def delete_channel(
    ch_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("notify:manage")),
    db: Session = Depends(get_db),
):
    ok = notify_service.delete_channel(db, ch_id, current.project_id)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("通知渠道")
    db.commit()
    _audit(req, current, db, "notify:channel:delete", f"#{ch_id}")
    return R.ok({"deleted": True})


@router.post("/test", response_model=R[dict], summary="测试通知发送")
def test_notify(
    body: dict,
    req: Request,
    current: CurrentUser = Depends(require_permission("notify:manage")),
    db: Session = Depends(get_db),
):
    """向项目下所有启用的渠道发送测试通知。"""
    result = notify_service.notify_sync(
        db, current.project_id,
        event="plan_done",
        data={
            "plan_name": "测试计划(通知测试)",
            "result_summary": "通过 5 / 失败 0 / 跳过 0",
            "link": "-",
        },
    )
    _audit(req, current, db, "notify:test", "send test notification")
    return R.ok(result)
