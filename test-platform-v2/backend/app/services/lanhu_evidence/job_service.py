"""蓝湖证据包服务 —— 任务/页面/资产查询与级联删除的薄层。

Batch 181（FIX-173-P2-10）路由拆分：lanhu_evidence_*.py 路由文件不再直连 ORM，
Job/Page/Asset 查询与 536-550 的级联删除收敛至此。
约定：签名 (db, ...)，沿用调用方会话，不负责 commit（路由中原 db.commit() 保留在路由层）。
"""
from __future__ import annotations

import json as _json
import shutil as _shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.lanhu_evidence import (
    LanhuEvidenceAsset,
    LanhuEvidenceJob,
    LanhuEvidencePage,
    LanhuOcrBlock,
)
from app.services.lanhu_evidence.quality_service import evaluate_job_quality


def get_job(db: Session, job_id: int, project_id: int) -> LanhuEvidenceJob:
    """按 id + 项目归属取任务，不存在/越权抛 404（保持原路由 _get_job 语义）。"""
    job = db.get(LanhuEvidenceJob, job_id)
    if job is None or job.project_id != project_id:
        raise APIException(code=404, msg="证据包任务不存在", http_status=404)
    return job


def list_jobs(
    db: Session, project_id: int, page: int, page_size: int
) -> tuple[list[LanhuEvidenceJob], int]:
    """分页列出项目内任务（按 id 倒序），返回 (rows, total)。"""
    total = db.execute(
        select(func.count(LanhuEvidenceJob.id)).where(LanhuEvidenceJob.project_id == project_id)
    ).scalar_one()
    rows = db.execute(
        select(LanhuEvidenceJob)
        .where(LanhuEvidenceJob.project_id == project_id)
        .order_by(LanhuEvidenceJob.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), int(total)


def create_job(
    db: Session,
    *,
    project_id: int,
    source_url: str,
    creator_id: int,
    requested_options_json: str,
    storage_base: Path,
) -> LanhuEvidenceJob:
    """构造并 flush 新采集任务（status=pending/stage=queued），commit/refresh 由路由层负责。"""
    job = LanhuEvidenceJob(
        project_id=project_id,
        source_url=source_url,
        status="pending",
        stage="queued",
        creator_id=creator_id,
        requested_options_json=requested_options_json,
    )
    db.add(job)
    db.flush()
    job.storage_dir = str(storage_base / str(job.id) / "attempt-1")
    return job


def create_retry_job(
    db: Session,
    *,
    old_job: LanhuEvidenceJob,
    creator_id: int,
    storage_base: Path,
) -> LanhuEvidenceJob:
    """基于旧任务构造重试任务（attempt_no+1、parent_job_id 溯源），commit 由路由层负责。"""
    job = LanhuEvidenceJob(
        project_id=old_job.project_id,
        source_url=old_job.source_url,
        doc_id=old_job.doc_id,
        version_id=old_job.version_id,
        root_page_id=old_job.root_page_id,
        document_name=old_job.document_name,
        status="pending",
        stage="queued",
        creator_id=creator_id,
        parent_job_id=old_job.id,
        attempt_no=old_job.attempt_no + 1,
        requested_options_json=old_job.requested_options_json,
    )
    db.add(job)
    db.flush()
    job.storage_dir = str(storage_base / str(job.id) / f"attempt-{job.attempt_no}")
    return job


def list_pages(db: Session, job_id: int, project_id: int) -> list[LanhuEvidencePage]:
    """任务下的页面列表（按 order_index 排序）。"""
    return list(db.execute(
        select(LanhuEvidencePage)
        .where(LanhuEvidencePage.job_id == job_id, LanhuEvidencePage.project_id == project_id)
        .order_by(LanhuEvidencePage.order_index)
    ).scalars().all())


def get_page(db: Session, page_id: int, project_id: int) -> LanhuEvidencePage:
    """按 id + 项目归属取页面，不存在/越权抛 404。"""
    row = db.get(LanhuEvidencePage, page_id)
    if row is None or row.project_id != project_id:
        raise APIException(code=404, msg="页面不存在", http_status=404)
    return row


def list_assets(db: Session, job_id: int, project_id: int) -> list[LanhuEvidenceAsset]:
    """任务下的资产列表（按 id 排序）。"""
    return list(db.execute(
        select(LanhuEvidenceAsset)
        .where(
            LanhuEvidenceAsset.job_id == job_id,
            LanhuEvidenceAsset.project_id == project_id,
        )
        .order_by(LanhuEvidenceAsset.id)
    ).scalars().all())


def get_asset(db: Session, asset_id: int, project_id: int) -> LanhuEvidenceAsset:
    """按 id + 项目归属取资产，不存在/越权抛 404。"""
    asset = db.get(LanhuEvidenceAsset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise APIException(code=404, msg="资产不存在", http_status=404)
    return asset


def reevaluate_job_quality(db: Session, job_id: int, project_id: int) -> dict:
    """人工审核后重新评估父任务质量报告与状态（原路由 _reevaluate_job_quality）。"""
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


def delete_job_cascade(db: Session, job: LanhuEvidenceJob) -> None:
    """删除任务：清理磁盘存储目录（best-effort）并级联删除 OCR 块/资产/页面/job。

    原路由 519-550 的批量删除逻辑；commit 由路由层负责。
    """
    # 1. 清理磁盘存储目录（best-effort）
    if job.storage_dir:
        try:
            dir_path = Path(job.storage_dir).resolve()
            if dir_path.exists():
                _shutil.rmtree(str(dir_path), ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

    # 2. 级联删除关联数据库记录（子→父）
    # 先收集关联 page_id
    page_ids_raw = db.execute(
        select(LanhuEvidencePage.id).where(LanhuEvidencePage.job_id == job.id)
    ).scalars().all()
    page_id_list = list(page_ids_raw)

    # 删除 OCR 块
    db.query(LanhuOcrBlock).filter(LanhuOcrBlock.job_id == job.id).delete(synchronize_session=False)
    # 删除页面级资产
    if page_id_list:
        db.query(LanhuEvidenceAsset).filter(
            LanhuEvidenceAsset.page_id.in_(page_id_list)
        ).delete(synchronize_session=False)
    # 删除 job 级资产（无 page_id 的资产）
    db.query(LanhuEvidenceAsset).filter(LanhuEvidenceAsset.job_id == job.id).delete(synchronize_session=False)
    # 删除页面
    db.query(LanhuEvidencePage).filter(LanhuEvidencePage.job_id == job.id).delete(synchronize_session=False)
    # 删除 job
    db.delete(job)
