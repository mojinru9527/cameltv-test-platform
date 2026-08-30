"""蓝湖证据包 API 路由（任务/cookie/登录） —— /api/v1/lanhu-evidence/*

Batch 181（FIX-173-P2-10）路由拆分：原 lanhu_evidence.py 拆分为
lanhu_evidence_jobs.py（本文件）/ lanhu_evidence_assets.py / lanhu_evidence_review.py。
端点函数体逐字移动，仅调整 import；ORM 查询收敛至 app.services.lanhu_evidence.job_service。
"""
from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.lanhu_evidence import (
    LanhuEvidenceCreateRequest,
    LanhuEvidenceJobOut,
)
from app.services.lanhu_evidence import job_service

router = APIRouter(prefix="/lanhu-evidence", tags=["蓝湖证据包"])
logger = logging.getLogger(__name__)


def _require_enabled() -> None:
    if not settings.lanhu_evidence_enabled:
        raise APIException(code=503, msg="蓝湖证据包未启用（lanhu_evidence_enabled=False）", http_status=503)


def _storage_base() -> Path:
    if settings.lanhu_evidence_storage_dir:
        return Path(settings.lanhu_evidence_storage_dir)
    return Path(__file__).resolve().parent.parent.parent.parent / "storage" / "lanhu-evidence"


def _kick_evidence_worker() -> None:
    """Attempt immediate pickup after durable enqueue; scheduler polling remains fallback."""
    try:
        from app.services.lanhu_evidence.worker import poll_and_execute_evidence_jobs

        poll_and_execute_evidence_jobs()
    except Exception:  # noqa: BLE001
        # The job is already durable. A transient kick failure must not make the
        # request look failed; the scheduled worker will retry the pickup.
        logger.exception("Failed to kick Lanhu evidence worker after enqueue")


class LanhuCookieUpdateRequest(BaseModel):
    cookie: str = ""
    clear: bool = False


class LanhuLoginRequest(BaseModel):
    username: str = ""
    password: str = ""


@router.post("/cookie", response_model=R[dict], summary="保存/清除蓝湖 Cookie（Batch 133）")
def update_lanhu_cookie(
    body: LanhuCookieUpdateRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
):
    """保存用户更新的蓝湖 Cookie（重新登录后粘贴），后续采集自动使用；仅存 Cookie，不存密码。"""
    _require_enabled()
    from app.services.external import lanhu_provider

    if body.clear:
        lanhu_provider.clear_lanhu_cookie()
        return R.ok({"saved": False, "cleared": True})
    try:
        lanhu_provider.set_lanhu_cookie(body.cookie)
    except ValueError as exc:
        return R(code=400, msg=str(exc))
    return R.ok({"saved": True, "cleared": False})


@router.post("/login", response_model=R[dict], summary="蓝湖重新登录（Batch 133，尽力而为）")
async def lanhu_relogin(
    body: LanhuLoginRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
):
    """用蓝湖账号密码尝试重新登录并保存新 Cookie。

    依赖 lanhu-mcp 提供 lanhu_login 自动登录能力；当前 pinned 子模块未提供时，
    明确返回"请粘贴 Cookie / 联系管理员更新 LANHU_COOKIE"的兜底指引。
    """
    _require_enabled()
    from app.services.external import lanhu_provider

    runtime = lanhu_provider._load_lanhu_runtime()
    if runtime.login is None:
        return R.ok({
            "ok": False,
            "message": "自动登录暂不可用（lanhu-mcp 未提供 lanhu_login）。请手动登录蓝湖后粘贴 Cookie，或联系管理员更新 LANHU_COOKIE。",
        })
    if not body.username or not body.password:
        return R(code=400, msg="请填写蓝湖账号与密码")
    try:
        cookie = await runtime.login(username=body.username, password=body.password)
    except Exception as exc:  # noqa: BLE001
        return R.ok({
            "ok": False,
            "message": f"蓝湖自动登录失败（可能存在验证码/风控）：{str(exc)[:200]}。请手动登录后粘贴 Cookie。",
        })
    if not cookie:
        return R.ok({
            "ok": False,
            "message": "蓝湖自动登录未获取到 Cookie。请手动登录后粘贴 Cookie。",
        })
    lanhu_provider.set_lanhu_cookie(cookie)
    return R.ok({"ok": True, "message": "登录成功，Cookie 已保存，可重新提交蓝湖链接采集。"})


@router.post("/jobs", response_model=R[LanhuEvidenceJobOut], summary="创建蓝湖证据包采集任务")
def create_job(
    body: LanhuEvidenceCreateRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    _require_enabled()
    project_id = current.project_id or 0
    requested_import = any((
        body.import_to_requirement,
        body.import_to_knowledge,
        body.import_to_wiki,
    ))
    if requested_import:
        from app.services import rbac_service

        if not rbac_service.has_permission(
            current.permissions, "lanhu_evidence:import",
        ):
            raise APIException(
                code=403,
                msg="缺少权限：lanhu_evidence:import",
                http_status=403,
            )
    import json as _json
    job = job_service.create_job(
        db,
        project_id=project_id,
        source_url=body.url,
        creator_id=current.user.id,
        requested_options_json=_json.dumps(body.model_dump(), ensure_ascii=False),
        storage_base=_storage_base(),
    )
    db.commit()
    db.refresh(job)
    _kick_evidence_worker()
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.get("/jobs", response_model=R[Page[LanhuEvidenceJobOut]], summary="证据包任务列表")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    rows, total = job_service.list_jobs(db, project_id, page, page_size)
    return R.ok(Page(
        items=[LanhuEvidenceJobOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/jobs/{job_id}", response_model=R[LanhuEvidenceJobOut], summary="证据包任务详情")
def get_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    job = job_service.get_job(db, job_id, current.project_id or 0)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.post("/jobs/{job_id}/cancel", response_model=R[LanhuEvidenceJobOut], summary="取消证据包任务")
def cancel_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    job = job_service.get_job(db, job_id, current.project_id or 0)
    if job.status in ("pending", "running"):
        from datetime import datetime
        stale_seconds = int(getattr(settings, 'lanhu_evidence_stale_after_seconds', None) or 600)
        last_seen = job.heartbeat_at or job.started_at or job.updated_at or job.created_at
        if last_seen is not None and (datetime.now() - last_seen).total_seconds() > stale_seconds:
            # Stale job — force cancel directly
            job.status = "cancelled"
            job.stage = "done"
            job.finished_at = datetime.now()
            job.error_message = (job.error_message or "") + " (stale — force cancelled)"
        else:
            job.cancel_requested = True
        db.commit()
        db.refresh(job)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.post("/jobs/{job_id}/retry", response_model=R[LanhuEvidenceJobOut], summary="重试证据包任务")
def retry_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    _require_enabled()
    project_id = current.project_id or 0
    old = job_service.get_job(db, job_id, project_id)
    if old.status in ("pending", "running"):
        from datetime import datetime
        stale_seconds = int(getattr(settings, 'lanhu_evidence_stale_after_seconds', None) or 600)
        last_seen = old.heartbeat_at or old.started_at or old.updated_at or old.created_at
        if last_seen is None or (datetime.now() - last_seen).total_seconds() > stale_seconds:
            # Auto-fail stuck job so retry can proceed
            old.status = "failed"
            old.stage = "done"
            old.error_message = (old.error_message or "") + " (stale — auto-failed for retry)"
            if old.finished_at is None:
                old.finished_at = datetime.now()
            db.commit()
        else:
            raise APIException(code=409, msg="运行中的任务不可重试", http_status=409)
    job = job_service.create_retry_job(
        db,
        old_job=old,
        creator_id=current.user.id,
        storage_base=_storage_base(),
    )
    db.commit()
    db.refresh(job)
    _kick_evidence_worker()
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.delete("/jobs/{job_id}", response_model=R[dict], summary="删除证据包任务及其所有关联数据")
def delete_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    """删除证据包任务：级联删除页面、资产、OCR块和任务自身，并清理磁盘存储目录。"""
    project_id = current.project_id or 0
    job = job_service.get_job(db, job_id, project_id)
    job_service.delete_job_cascade(db, job)
    db.commit()
    return R.ok({"deleted": True, "job_id": job_id})
