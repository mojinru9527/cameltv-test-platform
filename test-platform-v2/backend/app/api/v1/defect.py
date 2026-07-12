"""Defect API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db, require_permission
from app.schemas.common import R
from app.schemas.defect import DefectCreate, DefectOut, DefectStats, DefectUpdate
from app.services import defect_service
from app.services.audit_service import write_audit
from app.services.knowledge import ingest_service
from app.models.user import User

logger = logging.getLogger("defect")
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


def _run_notify_in_new_session(project_id: int, event: str, data: dict) -> None:
    """P1-4/S4a: 在独立 DB session 中发送通知（供 BackgroundTasks 调用）。

    必须使用独立的 SessionLocal()，因为 BackgroundTasks 在响应返回后执行，
    原请求的 db session 可能已关闭。
    """
    from app.core.db import SessionLocal
    from app.services.notify_service import notify_sync

    db = SessionLocal()
    try:
        notify_sync(db, project_id, event, data)
    except Exception:
        logger.exception("Background notification failed: event=%s project=%s", event, project_id)
    finally:
        db.close()


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
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("defect:create")),
    db: Session = Depends(get_db),
):
    r = defect_service.create_defect(db, body, current.user.id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "defect:create", f"#{r['id']} {r['title']}")
    # 知识入库：缺陷 → 知识源/切片（post-commit，自带 Session）
    background_tasks.add_task(
        ingest_service.ingest_defect_in_new_session, current.project_id or 0, r["id"]
    )

    # P1-4/S4a: Background notification via FastAPI BackgroundTasks
    # (replaces fire-and-forget asyncio.create_task — task is tracked and
    # runs in its own DB session to avoid session-closed errors).
    if body.assignee_id and body.assignee_id > 0:
        assignee = db.get(User, body.assignee_id)
        assignee_name = (assignee.nickname or assignee.username) if assignee else ""
        background_tasks.add_task(
            _run_notify_in_new_session,
            current.project_id or 0,
            "defect_assigned",
            {
                "title": body.title,
                "severity": body.severity,
                "assignee": assignee_name,
                "status": "open",
                "link": "",
            },
        )

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
    background_tasks: BackgroundTasks,
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
    # 知识入库：状态变更后重新沉淀缺陷（关闭时含处理说明）
    background_tasks.add_task(
        ingest_service.ingest_defect_in_new_session, current.project_id or 0, defect_id
    )
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
    # P1-S6a: Content-Length 前置检查，避免读取超大文件
    content_length = req.headers.get("content-length")
    if content_length:
        cl = int(content_length)
        max_bytes = 50 * 1024 * 1024
        if cl > max_bytes:
            from app.core.exceptions import APIException
            raise APIException(
                f"上传文件超过限制 (max: 50 MB, got: {cl / (1024*1024):.1f} MB)",
                code=413,
            )
    # P1-5b: 直接读取（Content-Length 已做前置检查，max 50 MB；upload_attachment
    # 需要完整 bytes，流式写入临时文件后再次读回不能节省峰值内存）。
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


# ── V2.6: External sync endpoints ──

@router.post("/{defect_id}/sync-push", response_model=R[dict])
def sync_push_defect(
    defect_id: int,
    integration_id: int = Query(..., description="Integration config ID to push to"),
    current: CurrentUser = Depends(require_permission("integration:sync")),
    db: Session = Depends(get_db),
):
    """Push a single defect to the external system."""
    from app.services.sync import engine as sync_engine

    log_entry = sync_engine.push_defect(db, integration_id, defect_id, current.project_id or 0)
    return R.ok(log_entry)


@router.post("/{defect_id}/sync-pull", response_model=R[dict])
def sync_pull_defect(
    defect_id: int,
    integration_id: int = Query(..., description="Integration config ID to pull from"),
    current: CurrentUser = Depends(require_permission("integration:sync")),
    db: Session = Depends(get_db),
):
    """Pull latest status for a single defect from the external system."""
    from app.services.sync import engine as sync_engine

    log_entry = sync_engine.pull_defect_status(db, integration_id, defect_id, current.project_id or 0)
    return R.ok(log_entry)
