"""蓝湖证据包 API 路由（人工审核） —— /api/v1/lanhu-evidence/*

Batch 181（FIX-173-P2-10）路由拆分：原 lanhu_evidence.py 拆分为
lanhu_evidence_jobs.py / lanhu_evidence_assets.py / lanhu_evidence_review.py（本文件）。
端点函数体逐字移动，仅调整 import；ORM 查询与质量重评估收敛至
app.services.lanhu_evidence.job_service。
"""
from __future__ import annotations

import json as _json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R
from app.schemas.lanhu_evidence import (
    LanhuEvidencePageOut,
    LanhuEvidencePageReviewRequest,
)
from app.services.lanhu_evidence import job_service

router = APIRouter(prefix="/lanhu-evidence", tags=["蓝湖证据包-审核"])


@router.post("/pages/{page_id}/review", response_model=R[LanhuEvidencePageOut],
             summary="人工审核证据页（OCR 缺失豁免）")
def review_page(
    page_id: int,
    body: LanhuEvidencePageReviewRequest,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:review")),
    db: Session = Depends(get_db),
):
    project_id = current.project_id or 0
    row = job_service.get_page(db, page_id, project_id)
    job = job_service.get_job(db, row.job_id, project_id)
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
    quality = job_service.reevaluate_job_quality(db, row.job_id, project_id)
    db.commit()

    # If the final review opens the quality gate, complete the import options
    # that were already authorized and persisted when the job was created.
    if quality.get("import_ready") and not previous_quality.get("import_ready"):
        job = job_service.get_job(db, row.job_id, project_id)
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
                job = job_service.get_job(db, row.job_id, project_id)
                job.import_result_json = _json.dumps(
                    result, ensure_ascii=False, default=str,
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                job = job_service.get_job(db, row.job_id, project_id)
                if job is not None:
                    job.import_result_json = _json.dumps(
                        {"error": str(exc)[:500]}, ensure_ascii=False,
                    )
                    db.commit()
    db.refresh(row)
    return R.ok(LanhuEvidencePageOut.model_validate(row))
