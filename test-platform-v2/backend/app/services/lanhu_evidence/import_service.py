"""证据包导入 —— 需求文档 / RAG 知识源 / Wiki Raw Source。

从证据包（DB 中的 LanhuEvidencePage.merged_text，系统真源）生成下游资产，
每条都携带 evidence_job_id / doc_id / version_id / page_id 以便回溯到截图与蓝湖原页。
LLM 摘要（若有）发生在后续编译，永不覆盖证据文本。
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage
from app.services import requirement_service
from app.services.knowledge import chunk_service, source_service
from app.services.wiki import raw_source_service


def _load_job_and_pages(db: Session, project_id: int, job_id: int) -> tuple[LanhuEvidenceJob, list[LanhuEvidencePage]]:
    job = db.get(LanhuEvidenceJob, job_id)
    if job is None or job.project_id != project_id:
        raise ValueError("证据包任务不存在")
    pages = db.execute(
        select(LanhuEvidencePage)
        .where(LanhuEvidencePage.job_id == job_id, LanhuEvidencePage.project_id == project_id)
        .order_by(LanhuEvidencePage.order_index)
    ).scalars().all()
    return job, list(pages)


def _job_title(job: LanhuEvidenceJob) -> str:
    return f"蓝湖证据包 {job.document_name or job.doc_id or job.id}".strip()


def _combined_text(job: LanhuEvidenceJob, pages: list[LanhuEvidencePage]) -> str:
    parts = [f"# {_job_title(job)}", f"来源链接：{job.source_url}", ""]
    for p in pages:
        parts.append(p.merged_text or f"# {p.page_name}")
        parts.append("")
    return "\n".join(parts).strip()


def _job_metadata(job: LanhuEvidenceJob) -> dict:
    return {
        "evidence_job_id": job.id,
        "word_path": job.word_path,
        "json_path": job.json_path,
        "doc_id": job.doc_id,
        "version_id": job.version_id,
    }


def import_to_requirement(db: Session, *, project_id: int, job_id: int, creator_id: int = 0) -> dict:
    """从证据包生成一个正式需求文档（file_type=docx，source_ref=蓝湖 URL）。"""
    job, pages = _load_job_and_pages(db, project_id, job_id)
    doc = requirement_service.create_requirement(
        db,
        project_id=project_id,
        creator_id=creator_id,
        title=_job_title(job),
        file_type="docx",
        source_ref=job.source_url,
        content=_combined_text(job, pages),
    )
    return doc


def import_to_knowledge(db: Session, *, project_id: int, job_id: int) -> int | None:
    """写入一条 RAG 知识源 + 逐页 chunk（chunk_type=requirement_page，携带来源引用）。"""
    job, pages = _load_job_and_pages(db, project_id, job_id)
    source = source_service.record_source(
        db,
        project_id=project_id,
        source_type="lanhu_evidence",
        source_id=job.id,
        title=_job_title(job),
        source_ref=job.source_url,
        raw_content=_combined_text(job, pages),
        version=job.version_id or "",
        metadata=_job_metadata(job),
    )
    if source is None:
        return None
    chunks = [
        {
            "chunk_type": "requirement_page",
            "title": p.page_path or p.page_name,
            "content": p.merged_text or "",
            "tags": ["lanhu", "ocr", p.folder or ""],
        }
        for p in pages
        if (p.merged_text or "").strip()
    ]
    if chunks:
        chunk_service.make_chunks(db, source, chunks)
    db.commit()
    return source.id


def import_to_wiki(db: Session, *, project_id: int, job_id: int) -> int | None:
    """写入一条 Wiki Raw Source（不可变事实层，immutable_version 追溯到蓝湖版本+任务）。"""
    job, pages = _load_job_and_pages(db, project_id, job_id)
    content_md = _combined_text(job, pages)
    content_hash = hashlib.sha256(content_md.encode("utf-8")).hexdigest()
    immutable_version = f"lanhu-evidence:{job.doc_id}:{job.version_id}:{job.id}"
    raw = raw_source_service.record_raw_source(
        db,
        project_id=project_id,
        source_type="lanhu_evidence",
        source_ref=job.source_url,
        title=_job_title(job),
        content_md=content_md,
        content_hash=content_hash,
        immutable_version=immutable_version,
        metadata=_job_metadata(job),
    )
    if raw is None:
        return None
    db.commit()
    return raw.id
