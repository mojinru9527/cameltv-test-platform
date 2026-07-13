"""蓝湖证据包 API 路由 —— /api/v1/lanhu-evidence/*

启动证据包采集任务（异步后台）→ 查询任务/页面/资产 → 导入需求/RAG/Wiki。
受 lanhu_evidence_enabled 门禁（默认 OFF → 503）与 RBAC（lanhu_evidence:*）保护，项目级隔离。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.models.lanhu_evidence import (
    LanhuEvidenceAsset,
    LanhuEvidenceJob,
    LanhuEvidencePage,
)
from app.schemas.common import Page, R
from app.schemas.lanhu_evidence import (
    LanhuEvidenceAssetOut,
    LanhuEvidenceCreateRequest,
    LanhuEvidenceImportRequest,
    LanhuEvidenceJobOut,
    LanhuEvidencePageOut,
)
from app.services.lanhu_evidence import job_runner

router = APIRouter(prefix="/lanhu-evidence", tags=["蓝湖证据包"])


def _require_enabled() -> None:
    if not settings.lanhu_evidence_enabled:
        raise APIException(code=503, msg="蓝湖证据包未启用（lanhu_evidence_enabled=False）", http_status=503)


def _storage_base() -> Path:
    if settings.lanhu_evidence_storage_dir:
        return Path(settings.lanhu_evidence_storage_dir)
    return Path(__file__).resolve().parent.parent.parent.parent / "storage" / "lanhu-evidence"


def _get_job(db: Session, job_id: int, project_id: int) -> LanhuEvidenceJob:
    job = db.get(LanhuEvidenceJob, job_id)
    if job is None or job.project_id != project_id:
        raise APIException(code=404, msg="证据包任务不存在", http_status=404)
    return job


@router.post("/jobs", response_model=R[LanhuEvidenceJobOut], summary="创建蓝湖证据包采集任务")
def create_job(
    body: LanhuEvidenceCreateRequest,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    _require_enabled()
    project_id = current.project_id or 0
    job = LanhuEvidenceJob(
        project_id=project_id,
        source_url=body.url,
        status="pending",
        stage="queued",
        creator_id=current.user.id,
    )
    db.add(job)
    db.flush()
    job.storage_dir = str(_storage_base() / str(job.id))
    db.commit()
    db.refresh(job)
    background_tasks.add_task(job_runner.run_job_in_new_session, job.id, project_id)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.get("/jobs", response_model=R[Page[LanhuEvidenceJobOut]], summary="证据包任务列表")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    base = select(LanhuEvidenceJob).where(LanhuEvidenceJob.project_id == project_id)
    total = db.execute(
        select(func.count(LanhuEvidenceJob.id)).where(LanhuEvidenceJob.project_id == project_id)
    ).scalar_one()
    rows = db.execute(
        base.order_by(LanhuEvidenceJob.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
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
    job = _get_job(db, job_id, current.project_id or 0)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.get("/jobs/{job_id}/pages", response_model=R[Page[LanhuEvidencePageOut]], summary="证据包页面列表")
def list_pages(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    _get_job(db, job_id, project_id)
    rows = db.execute(
        select(LanhuEvidencePage)
        .where(LanhuEvidencePage.job_id == job_id, LanhuEvidencePage.project_id == project_id)
        .order_by(LanhuEvidencePage.order_index)
    ).scalars().all()
    return R.ok(Page(
        items=[LanhuEvidencePageOut.model_validate(r) for r in rows],
        total=len(rows), page=1, page_size=len(rows) or 1,
    ))


@router.get("/pages/{page_id}", response_model=R[LanhuEvidencePageOut], summary="证据包页面详情")
def get_page(
    page_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    row = db.get(LanhuEvidencePage, page_id)
    if row is None or row.project_id != project_id:
        raise APIException(code=404, msg="页面不存在", http_status=404)
    return R.ok(LanhuEvidencePageOut.model_validate(row))


@router.get("/assets/{asset_id}", summary="下载证据包资产（截图/Word/JSON）")
def download_asset(
    asset_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    asset = db.get(LanhuEvidenceAsset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise APIException(code=404, msg="资产不存在", http_status=404)
    # 项目隔离 + 路径逃逸防护：解析后须落在任务 storage_dir 内
    job = db.get(LanhuEvidenceJob, asset.job_id)
    file_path = Path(asset.file_path).resolve()
    if job and job.storage_dir:
        base = Path(job.storage_dir).resolve()
        if not str(file_path).startswith(str(base)):
            raise APIException(code=403, msg="资产路径越权", http_status=403)
    if not file_path.exists():
        raise APIException(code=404, msg="资产文件缺失", http_status=404)
    return FileResponse(str(file_path), filename=file_path.name)


@router.post("/jobs/{job_id}/cancel", response_model=R[LanhuEvidenceJobOut], summary="取消证据包任务")
def cancel_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    job = _get_job(db, job_id, current.project_id or 0)
    if job.status in ("pending", "running"):
        job.cancel_requested = True
        db.commit()
        db.refresh(job)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.post("/jobs/{job_id}/retry", response_model=R[LanhuEvidenceJobOut], summary="重试证据包任务")
def retry_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    _require_enabled()
    project_id = current.project_id or 0
    job = _get_job(db, job_id, project_id)
    job.status = "pending"
    job.stage = "queued"
    job.cancel_requested = False
    job.error_message = ""
    db.commit()
    background_tasks.add_task(job_runner.run_job_in_new_session, job.id, project_id)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))


@router.post("/jobs/{job_id}/import", response_model=R[dict], summary="导入证据包到需求/RAG/Wiki")
def import_job(
    job_id: int,
    body: LanhuEvidenceImportRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:import")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    job = _get_job(db, job_id, project_id)
    if job.status not in ("success", "success_with_warnings"):
        raise APIException(code=400, msg="任务未成功完成，无法导入", http_status=400)

    from app.services.lanhu_evidence import import_service

    result: dict = {}
    if body.import_to_requirement:
        result["requirement"] = import_service.import_to_requirement(
            db, project_id=project_id, job_id=job.id, creator_id=current.user.id,
        )
    if body.import_to_knowledge:
        result["knowledge_source_id"] = import_service.import_to_knowledge(
            db, project_id=project_id, job_id=job.id,
        )
    if body.import_to_wiki:
        result["wiki_raw_source_id"] = import_service.import_to_wiki(
            db, project_id=project_id, job_id=job.id,
        )
    return R.ok(result)
