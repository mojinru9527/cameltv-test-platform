"""LLM-Wiki 差异对比 API 路由（差异域） —— /api/v1/wiki/*

Batch 181（FIX-173-P2-10）路由拆分：差异任务 / 差异项 / 转待审 AI 产物。
端点函数体与原 wiki.py 逐字一致；WikiDiffTask/WikiDiffItem ORM 查询收敛到
app.services.wiki.compare_service。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.wiki import (
    WikiDiffCreateArtifactRequest,
    WikiDiffCreateArtifactResult,
    WikiDiffCreateRequest,
    WikiDiffItemOut,
    WikiDiffItemReviewRequest,
    WikiDiffTaskBrief,
    WikiDiffTaskOut,
)
from app.services import audit_service
from app.services.wiki import compare_service

router = APIRouter(prefix="/wiki", tags=["Wiki 差异"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _require_wiki_diff_enabled() -> None:
    if not settings.wiki_diff_enabled:
        raise APIException(code=503, msg="知识差异对比未启用（wiki_diff_enabled=False）", http_status=503)


# ═══════════════════════════════════════════════════════
# 知识库差异对比（VNext-3）
# ═══════════════════════════════════════════════════════

@router.post("/diff/tasks", response_model=R[WikiDiffTaskOut], summary="发起知识库差异对比")
def create_diff_task(
    body: WikiDiffCreateRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:diff")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    pid = current.project_id or 0
    task = compare_service.create_diff_task(
        db,
        project_id=pid,
        title=body.title or f"{body.query} 差异对比",
        compare_type=body.compare_type,
        left_ref_json=json.dumps({"kb_type": body.left_kb_type, "query": body.query}, ensure_ascii=False),
        right_ref_json=json.dumps({"kb_type": body.right_kb_type, "query": body.query}, ensure_ascii=False),
        created_by=current.user.id if current.user else 0,
    )
    _audit(req, current, db, action="wiki.diff.create", target=body.query, detail=f"task#{task.id}")
    db.commit()
    background_tasks.add_task(compare_service.run_diff_in_new_session, pid, task.id)
    return R.ok(WikiDiffTaskOut.model_validate(task))


@router.get("/diff/tasks", response_model=R[Page[WikiDiffTaskBrief]], summary="差异任务列表")
def list_diff_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    rows, total = compare_service.list_diff_tasks(
        db, pid, status=status, page=page, page_size=page_size)
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiDiffTaskBrief.model_validate(r) for r in rows]))


@router.get("/diff/tasks/{task_id}", response_model=R[WikiDiffTaskOut], summary="差异任务详情（含差异项）")
def get_diff_task(
    task_id: int,
    dimension: str | None = Query(None),
    diff_type: str | None = Query(None),
    severity: str | None = Query(None),
    review_status: str | None = Query(None),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    task = compare_service.get_diff_task(db, task_id, pid)
    if not task:
        return R(code=404, msg="任务不存在")
    items = compare_service.list_diff_items(
        db, task_id,
        dimension=dimension, diff_type=diff_type,
        severity=severity, review_status=review_status,
    )
    out = WikiDiffTaskOut.model_validate(task)
    out.items = [WikiDiffItemOut.model_validate(x) for x in items]
    return R.ok(out)


@router.post("/diff/items/{item_id}/accept", response_model=R[WikiDiffItemOut], summary="采纳差异项")
def accept_diff_item(
    item_id: int,
    body: WikiDiffItemReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    item = compare_service.get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "accepted"
    _audit(req, current, db, action="wiki.diff.accept", target=f"item#{item_id}",
           detail=f"{item.dimension}/{item.diff_type}")
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/reject", response_model=R[WikiDiffItemOut], summary="忽略差异项")
def reject_diff_item(
    item_id: int,
    body: WikiDiffItemReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    item = compare_service.get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "rejected"
    _audit(req, current, db, action="wiki.diff.reject", target=f"item#{item_id}",
           detail=f"{item.dimension}/{item.diff_type}")
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/create-artifact",
             response_model=R[WikiDiffCreateArtifactResult], summary="差异项转待审 AI 产物")
def create_artifact(
    item_id: int,
    body: WikiDiffCreateArtifactRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    pid = current.project_id or 0
    item = compare_service.get_diff_item(db, item_id, pid)
    if not item:
        return R(code=404, msg="差异项不存在")
    if item.resolved_artifact_id:
        return R(code=400, msg="该差异项已生成产物")
    art = compare_service.create_artifact_from_item(
        db, pid, item, artifact_type=body.artifact_type,
        operator_id=current.user.id if current.user else 0)
    _audit(req, current, db, action="wiki.diff.create_artifact", target=f"item#{item_id}",
           detail=f"artifact#{art.id} type={art.artifact_type}")
    db.commit()
    return R.ok(WikiDiffCreateArtifactResult(artifact_id=art.id, artifact_type=art.artifact_type))
