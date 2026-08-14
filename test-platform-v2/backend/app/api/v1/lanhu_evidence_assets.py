"""蓝湖证据包 API 路由（页面/资产/导入） —— /api/v1/lanhu-evidence/*

Batch 181（FIX-173-P2-10）路由拆分：原 lanhu_evidence.py 拆分为
lanhu_evidence_jobs.py / lanhu_evidence_assets.py（本文件）/ lanhu_evidence_review.py。
端点函数体逐字移动，仅调整 import；ORM 查询与级联删除收敛至
app.services.lanhu_evidence.job_service。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.lanhu_evidence import (
    LanhuEvidenceAssetOut,
    LanhuEvidenceImportRequest,
    LanhuEvidencePageOut,
)
from app.services.lanhu_evidence import job_service

router = APIRouter(prefix="/lanhu-evidence", tags=["蓝湖证据包-资产"])


@router.get("/jobs/{job_id}/pages", response_model=R[Page[LanhuEvidencePageOut]], summary="证据包页面列表")
def list_pages(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    job_service.get_job(db, job_id, project_id)
    rows = job_service.list_pages(db, job_id, project_id)
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
    row = job_service.get_page(db, page_id, project_id)
    return R.ok(LanhuEvidencePageOut.model_validate(row))


@router.get(
    "/jobs/{job_id}/assets",
    response_model=R[list[LanhuEvidenceAssetOut]],
    summary="List project-scoped evidence assets",
)
def list_assets(
    job_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    job_service.get_job(db, job_id, project_id)
    assets = job_service.list_assets(db, job_id, project_id)
    return R.ok([LanhuEvidenceAssetOut.model_validate(asset) for asset in assets])


@router.get("/assets/{asset_id}", summary="下载证据包资产（截图/Word/JSON）")
def download_asset(
    asset_id: int,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:view")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    asset = job_service.get_asset(db, asset_id, project_id)
    # 项目隔离 + 路径逃逸防护：解析后须落在任务 storage_dir 内
    job = job_service.get_job(db, asset.job_id, project_id)
    file_path = Path(asset.file_path).resolve()
    if not job.storage_dir:
        raise APIException(code=403, msg="资产路径越权", http_status=403)
    base = Path(job.storage_dir).resolve()
    if not file_path.is_relative_to(base):
        raise APIException(code=403, msg="资产路径越权", http_status=403)
    if not file_path.exists():
        raise APIException(code=404, msg="资产文件缺失", http_status=404)
    return FileResponse(str(file_path), filename=file_path.name)


@router.post("/jobs/{job_id}/import", response_model=R[dict], summary="导入证据包到需求/RAG/Wiki")
def import_job(
    job_id: int,
    body: LanhuEvidenceImportRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:import")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    job = job_service.get_job(db, job_id, project_id)
    if job.status != "success":
        raise APIException(
            code=409,
            msg="证据包存在告警或尚未成功完成，禁止导入需求/RAG/Wiki",
            http_status=409,
        )
    import json as _json

    from app.services.lanhu_evidence import import_service

    try:
        result = import_service.execute_requested_imports(
            db,
            job=job,
            options=body.model_dump(),
            creator_id=current.user.id,
        )
    except ValueError as exc:
        raise APIException(code=409, msg=str(exc), http_status=409) from exc
    job = job_service.get_job(db, job_id, project_id)
    job.import_result_json = _json.dumps(result, ensure_ascii=False, default=str)
    db.commit()
    return R.ok(result)
