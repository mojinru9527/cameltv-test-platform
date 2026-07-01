"""Defect API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db, require_permission
from app.schemas.common import R
from app.schemas.defect import DefectCreate, DefectOut, DefectStats, DefectUpdate
from app.services import defect_service
from app.services.audit_service import write_audit
from app.models.user import User

router = APIRouter(prefix="/defects", tags=["缺陷管理"])


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


@router.get("/stats", response_model=R[DefectStats])
def get_defect_stats(
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    stats = defect_service.get_defect_stats(db, current.project_id or 0)
    return R.ok(DefectStats(**stats))


@router.get("", response_model=R[dict])
def list_defects(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    assignee_id: int | None = Query(None),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    items, total = defect_service.list_defects(
        db,
        project_id=current.project_id or 0,
        severity=severity,
        status=status,
        assignee_id=assignee_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[DefectOut])
def create_defect(
    req: Request,
    body: DefectCreate,
    current: CurrentUser = Depends(require_permission("defect:create")),
    db: Session = Depends(get_db),
):
    r = defect_service.create_defect(db, body, current.user.id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "defect:create", f"#{r['id']} {r['title']}")

    # Background notification if assignee is set
    if body.assignee_id and body.assignee_id > 0:
        import asyncio
        from app.services.notify_service import notify
        assignee = db.get(User, body.assignee_id) if 'User' in dir() else None
        assignee_name = (assignee.nickname or assignee.username) if assignee else ""
        asyncio.create_task(notify(db, current.project_id or 0, "defect_assigned", {
            "title": body.title,
            "severity": body.severity,
            "assignee": assignee_name,
            "status": "open",
            "link": "",
        }))

    return R.ok(DefectOut(**r))


@router.get("/{defect_id}", response_model=R[DefectOut])
def get_defect(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:detail")),
    db: Session = Depends(get_db),
):
    r = defect_service.get_defect(db, defect_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    return R.ok(DefectOut(**r))


@router.put("/{defect_id}", response_model=R[DefectOut])
def update_defect(
    req: Request,
    defect_id: int,
    body: DefectUpdate,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    r = defect_service.update_defect(db, defect_id, body, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    db.commit()
    _audit(req, current, db, "defect:update", f"#{defect_id}")
    return R.ok(DefectOut(**r))


@router.delete("/{defect_id}", response_model=R[dict])
def delete_defect(
    req: Request,
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:delete")),
    db: Session = Depends(get_db),
):
    ok = defect_service.delete_defect(db, defect_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    db.commit()
    _audit(req, current, db, "defect:delete", f"defect #{defect_id}")
    return R.ok({"deleted": True})


# ── 状态流转 ──────────────────────────────────────────

from pydantic import BaseModel, Field


class TransitionBody(BaseModel):
    to_status: str = Field(..., description="目标状态: confirmed/fixing/pending_review/closed/rejected/open")
    comment: str = Field("", max_length=500)


@router.get("/{defect_id}/transitions", response_model=R[list], summary="缺陷流转历史")
def list_transitions(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:detail")),
    db: Session = Depends(get_db),
):
    """返回缺陷的完整流转时间线。"""
    history = defect_service.get_transitions(db, defect_id, current.project_id or 0)
    return R.ok(history)


@router.post("/{defect_id}/transition", response_model=R[DefectOut], summary="缺陷状态流转")
def transition_defect(
    req: Request,
    defect_id: int,
    body: TransitionBody,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    """将缺陷流转至新状态（校验合法流转路径）。"""
    try:
        r = defect_service.transition_defect(
            db, defect_id, body.to_status,
            project_id=current.project_id or 0,
            operator_id=current.user.id,
            operator_name=current.user.nickname or current.user.username,
            comment=body.comment,
        )
    except ValueError as e:
        from app.core.exceptions import APIException
        raise APIException(msg=str(e))
    if not r:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    db.commit()
    _audit(req, current, db, "defect:transition", f"#{defect_id} → {body.to_status}", body.comment)
    return R.ok(DefectOut(**r))


# ── 评论 ──────────────────────────────────────────────

class CommentBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.get("/{defect_id}/comments", response_model=R[list], summary="缺陷评论列表")
def list_comments(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:detail")),
    db: Session = Depends(get_db),
):
    comments = defect_service.list_comments(db, defect_id, current.project_id or 0)
    return R.ok(comments)


@router.post("/{defect_id}/comments", response_model=R[dict], summary="添加缺陷评论")
def add_comment(
    defect_id: int,
    body: CommentBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    c = defect_service.create_comment(
        db, defect_id, body.content,
        project_id=current.project_id or 0,
        author_id=current.user.id,
        author_name=current.user.nickname or current.user.username,
    )
    if c is None:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    db.commit()
    _audit(req, current, db, "defect:comment", f"#{defect_id}", body.content[:100])
    return R.ok(c)


# ── 附件上传/下载 ──────────────────────────────────────

@router.post("/{defect_id}/attachments", response_model=R[dict], summary="上传缺陷附件")
def upload_attachment(
    defect_id: int,
    req: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    """Upload a file attachment to a defect (max 50 MB)."""
    content = file.file.read()
    if len(content) > 50 * 1024 * 1024:
        from app.core.exceptions import APIException
        raise APIException("附件大小不能超过 50 MB", code=413)
    a = defect_service.upload_attachment(
        db, defect_id, file.filename or "unknown", content,
        project_id=current.project_id or 0,
        uploader_id=current.user.id,
        uploader_name=current.user.nickname or current.user.username,
    )
    if a is None:
        from app.core.exceptions import not_found
        raise not_found("缺陷")
    db.commit()
    _audit(req, current, db, "defect:attachment:upload", f"#{defect_id}", file.filename or "")
    return R.ok(a)


@router.get("/{defect_id}/attachments", response_model=R[list], summary="缺陷附件列表")
def list_attachments(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:detail")),
    db: Session = Depends(get_db),
):
    """List all attachments for a defect."""
    items = defect_service.list_attachments(db, defect_id, current.project_id or 0)
    return R.ok(items)


@router.get("/{defect_id}/attachments/{attachment_id}", summary="下载缺陷附件")
def download_attachment(
    defect_id: int,
    attachment_id: int,
    current: CurrentUser = Depends(require_permission("defect:detail")),
    db: Session = Depends(get_db),
):
    """Download an attachment file."""
    result = defect_service.get_attachment(db, attachment_id, current.project_id or 0)
    if not result:
        from app.core.exceptions import not_found
        raise not_found("附件")
    meta, file_path = result
    return FileResponse(
        str(file_path),
        filename=meta["filename"],
        media_type=meta["mime_type"],
    )


@router.delete("/{defect_id}/attachments/{attachment_id}", response_model=R[dict], summary="删除缺陷附件")
def delete_attachment(
    defect_id: int,
    attachment_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("defect:delete")),
    db: Session = Depends(get_db),
):
    """Delete an attachment (file + DB record)."""
    ok = defect_service.delete_attachment(db, attachment_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("附件")
    db.commit()
    _audit(req, current, db, "defect:attachment:delete", f"#{defect_id}", f"attachment #{attachment_id}")
    return R.ok({"deleted": True})
