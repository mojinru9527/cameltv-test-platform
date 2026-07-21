"""蓝湖证据包 API 路由 —— /api/v1/lanhu-evidence/*

持久化待处理采集任务（由调度 worker 执行）→ 查询任务/页面/资产 → 导入需求/RAG/Wiki。
受 lanhu_evidence_enabled 门禁（默认 OFF → 503）与 RBAC（lanhu_evidence:*）保护，项目级隔离。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
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
    LanhuEvidencePageReviewRequest,
)

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
    job = LanhuEvidenceJob(
        project_id=project_id,
        source_url=body.url,
        status="pending",
        stage="queued",
        creator_id=current.user.id,
        requested_options_json=_json.dumps(body.model_dump(), ensure_ascii=False),
    )
    db.add(job)
    db.flush()
    job.storage_dir = str(_storage_base() / str(job.id) / "attempt-1")
    db.commit()
    db.refresh(job)
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
    _get_job(db, job_id, project_id)
    assets = db.execute(
        select(LanhuEvidenceAsset)
        .where(
            LanhuEvidenceAsset.job_id == job_id,
            LanhuEvidenceAsset.project_id == project_id,
        )
        .order_by(LanhuEvidenceAsset.id)
    ).scalars().all()
    return R.ok([LanhuEvidenceAssetOut.model_validate(asset) for asset in assets])


def _reevaluate_job_quality(db: Session, job_id: int, project_id: int) -> dict:
    """人工审核后重新评估父任务质量报告与状态。"""
    import json as _json

    from app.services.lanhu_evidence.quality_service import evaluate_job_quality

    job = db.get(LanhuEvidenceJob, job_id)
    if job is None or job.project_id != project_id:
        return {}
    pages = db.execute(
        select(LanhuEvidencePage)
        .where(LanhuEvidencePage.job_id == job_id, LanhuEvidencePage.project_id == project_id)
        .order_by(LanhuEvidencePage.order_index)
    ).scalars().all()
    page_dicts = [{
        "capture_status": p.capture_status,
        "segment_count": p.segment_count,
        "capture_truncated": p.capture_truncated,
        "merged_text": p.merged_text,
        "ocr_status": p.ocr_status,
        "review_status": p.review_status,
    } for p in pages]
    # A page transaction can fail after discovery and therefore leave no row.
    # Preserve those discovered-but-unpersisted pages as explicit quality gaps;
    # otherwise approving the remaining rows could incorrectly reopen imports.
    page_dicts.extend({
        "capture_status": "failed",
        "segment_count": 0,
        "capture_truncated": True,
        "merged_text": "",
        "ocr_status": "unavailable",
        "review_status": "pending",
    } for _ in range(max(0, job.total_pages - len(pages))))
    quality = evaluate_job_quality(page_dicts)
    job.quality_json = _json.dumps(quality, ensure_ascii=False)
    # 仅在既有终态之间调整（不复活 failed/cancelled）
    if job.status in ("success", "success_with_warnings"):
        job.status = "success" if quality["complete"] else "success_with_warnings"
    return quality


@router.post("/pages/{page_id}/review", response_model=R[LanhuEvidencePageOut],
             summary="人工审核证据页（OCR 缺失豁免）")
def review_page(
    page_id: int,
    body: LanhuEvidencePageReviewRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:review")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    row = db.get(LanhuEvidencePage, page_id)
    if row is None or row.project_id != project_id:
        raise APIException(code=404, msg="页面不存在", http_status=404)
    import json as _json

    job = db.get(LanhuEvidenceJob, row.job_id)
    try:
        previous_quality = _json.loads(job.quality_json or "{}") if job else {}
    except (_json.JSONDecodeError, TypeError):
        previous_quality = {}
    if body.approved:
        # 仅允许对有截图且合并文本非空的页面批准
        if row.capture_status != "success" or not (row.merged_text or "").strip():
            raise APIException(code=400, msg="仅可批准有截图且合并文本非空的页面", http_status=400)
        row.review_status = "approved"
    else:
        row.review_status = "rejected"
    row.reviewer_id = current.user.id
    row.review_comment = body.comment
    row.reviewed_at = datetime.now()
    db.flush()
    quality = _reevaluate_job_quality(db, row.job_id, project_id)
    db.commit()

    # If the final review opens the quality gate, complete the import options
    # that were already authorized and persisted when the job was created.
    if quality.get("import_ready") and not previous_quality.get("import_ready"):
        job = db.get(LanhuEvidenceJob, row.job_id)
        try:
            options = _json.loads(job.requested_options_json or "{}") if job else {}
        except (_json.JSONDecodeError, TypeError):
            options = {}
        requested_import = any(options.get(key) for key in (
            "import_to_requirement",
            "import_to_knowledge",
            "import_to_wiki",
        ))
        if job is not None and requested_import:
            from app.services.lanhu_evidence.import_service import execute_requested_imports

            try:
                result = execute_requested_imports(
                    db,
                    job=job,
                    options=options,
                    creator_id=job.creator_id,
                )
                job = db.get(LanhuEvidenceJob, row.job_id)
                job.import_result_json = _json.dumps(
                    result, ensure_ascii=False, default=str,
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                job = db.get(LanhuEvidenceJob, row.job_id)
                if job is not None:
                    job.import_result_json = _json.dumps(
                        {"error": str(exc)[:500]}, ensure_ascii=False,
                    )
                    db.commit()
    db.refresh(row)
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
    if job is None or job.project_id != project_id:
        raise APIException(code=404, msg="证据包任务不存在", http_status=404)
    file_path = Path(asset.file_path).resolve()
    if not job.storage_dir:
        raise APIException(code=403, msg="资产路径越权", http_status=403)
    base = Path(job.storage_dir).resolve()
    if not file_path.is_relative_to(base):
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
        from datetime import datetime, timedelta
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
    old = _get_job(db, job_id, project_id)
    if old.status in ("pending", "running"):
        from datetime import datetime, timedelta
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
    job = LanhuEvidenceJob(
        project_id=project_id,
        source_url=old.source_url,
        doc_id=old.doc_id,
        version_id=old.version_id,
        root_page_id=old.root_page_id,
        document_name=old.document_name,
        status="pending",
        stage="queued",
        creator_id=current.user.id,
        parent_job_id=old.id,
        attempt_no=old.attempt_no + 1,
        requested_options_json=old.requested_options_json,
    )
    db.add(job)
    db.flush()
    job.storage_dir = str(
        _storage_base() / str(job.id) / f"attempt-{job.attempt_no}"
    )
    db.commit()
    db.refresh(job)
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
    # 质量门禁：仅 import_ready=true 的任务可导入；success_with_warnings 一律 409。
    import json as _json
    try:
        quality = _json.loads(job.quality_json or "{}")
    except (_json.JSONDecodeError, TypeError):
        quality = {}
    if job.status != "success" or not quality.get("import_ready"):
        raise APIException(
            code=409,
            msg="证据包质量未达标（存在缺截图/截断/缺文本/未审 OCR 页），禁止导入",
            http_status=409,
        )

    from app.services.lanhu_evidence import import_service

    result = import_service.execute_requested_imports(
        db,
        job=job,
        options=body.model_dump(),
        creator_id=current.user.id,
    )
    job = _get_job(db, job_id, project_id)
    job.import_result_json = _json.dumps(result, ensure_ascii=False, default=str)
    db.commit()
    return R.ok(result)
