"""蓝湖导入编排 —— 提取 → Raw Source → 可选(RAG 入库 + Wiki 编译任务)。

async 入口（await 蓝湖 provider），在请求 Session 内完成 raw source / knowledge_source /
wiki_ingest_job 的建立与绑定；仅把昂贵的向量嵌入放到 BackgroundTasks。所有失败以
extraction_status 表达，不抛异常。
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.wiki import WikiIngestJob, WikiRawSource
from app.schemas.wiki import LanhuImportRequest, LanhuImportResult
from app.services.external import lanhu_provider
from app.services.knowledge import chunk_service, source_service
from app.services.knowledge.sanitize import sanitize
from app.services.knowledge.vectorize import embed_pending_chunks_in_new_session
from app.services.wiki import raw_source_service

logger = logging.getLogger("wiki.import")

_MAX_RAW = 20000  # 与 knowledge/ingest_service 对齐


def _truncate(text: str) -> str:
    text = text or ""
    return text if len(text) <= _MAX_RAW else text[:_MAX_RAW] + "\n…(截断)"


def _ingest_to_rag(db: Session, project_id: int, *, title: str, source_ref: str, content: str) -> int | None:
    """把蓝湖内容同步进现有 RAG 知识库（KnowledgeSource + 切片）；返回 source_id。

    仅在 knowledge_ingest_enabled 时执行。向量嵌入由调用方在 BackgroundTasks 中触发。
    """
    if not settings.knowledge_ingest_enabled:
        return None
    raw = sanitize(_truncate(content))
    ks = source_service.record_source(
        db, project_id=project_id, source_type="requirement", source_id=None,
        title=title, source_ref=source_ref, raw_content=raw,
        metadata={"origin": "lanhu"},
    )
    if ks is None:  # 同内容已入库
        return None
    chunks = [
        {"chunk_type": "requirement_rule", "title": f"{title} #{i + 1}", "content": part}
        for i, part in enumerate(chunk_service.slice_text(raw))
    ]
    chunk_service.make_chunks(db, ks, chunks)
    return ks.id


async def import_lanhu(
    db: Session,
    *,
    project_id: int,
    operator_id: int,
    req: LanhuImportRequest,
    background_tasks: BackgroundTasks,
) -> LanhuImportResult:
    result = await lanhu_provider.extract(req.url)

    # 硬失败：不建 raw source，直接回状态供前端提示
    if result.extraction_status in ("auth_failed", "permission_denied", "invalid_url", "failed"):
        return LanhuImportResult(
            extraction_status=result.extraction_status,
            extraction_summary=result.extraction_summary,
        )

    # image_only 且无补充说明 → 提示补充，不入库
    if result.extraction_status == "image_only" and not (req.description or "").strip():
        return LanhuImportResult(
            extraction_status="image_only",
            extraction_summary="原型为图片无法提取文本，请填写补充说明后重试",
        )

    title = result.module_name or result.document_name or "蓝湖需求"
    # 补充说明并入内容，供 Wiki/RAG 一并沉淀
    content = result.content_md
    if (req.description or "").strip():
        content = (content + "\n\n## 补充说明\n" + req.description).strip()
    content_hash = result.content_hash or source_service.content_hash(content)

    raw = raw_source_service.record_raw_source(
        db, project_id=project_id, source_type="lanhu", source_ref=req.url,
        title=title, content_md=content, content_hash=content_hash,
        immutable_version=result.immutable_version,
        metadata={
            "doc_id": result.doc_id, "version_id": result.version_id, "page_id": result.page_id,
            "client_scope": result.client_scope, "changelog": result.changelog,
            "description": req.description,
        },
    )
    if raw is None:  # 幂等：同内容已导入，返回既有记录
        existing = db.scalar(
            select(WikiRawSource).where(
                WikiRawSource.project_id == project_id,
                WikiRawSource.content_hash == content_hash,
                WikiRawSource.status == "active",
            ).order_by(WikiRawSource.id.desc())
        )
        return LanhuImportResult(
            raw_source_id=existing.id if existing else None,
            knowledge_source_id=existing.knowledge_source_id if existing else None,
            extraction_status=result.extraction_status,
            extraction_summary="内容未变化，已存在相同来源（跳过重复导入）",
        )

    ks_id: int | None = None
    if req.target.ingest_knowledge:
        ks_id = _ingest_to_rag(db, project_id, title=title, source_ref=req.url, content=content)
        if ks_id:
            raw.knowledge_source_id = ks_id

    job: WikiIngestJob | None = None
    if req.target.build_wiki and settings.wiki_enabled:
        job = WikiIngestJob(
            project_id=project_id, raw_source_id=raw.id, status="pending",
            stage="analysis", operator_id=operator_id,
        )
        db.add(job)
        db.flush()

    db.commit()

    # 昂贵的向量嵌入放到响应后台
    if ks_id:
        background_tasks.add_task(embed_pending_chunks_in_new_session, project_id, ks_id)
    # Wiki 编译：wiki_auto_ingest_enabled 时自动触发两阶段编译
    if job and settings.wiki_auto_ingest_enabled:
        from app.services.wiki import ingest_service
        background_tasks.add_task(ingest_service.run_wiki_ingest_in_new_session, project_id, job.id)

    return LanhuImportResult(
        raw_source_id=raw.id,
        knowledge_source_id=ks_id,
        wiki_job_id=job.id if job else None,
        extraction_status=result.extraction_status,
        extraction_summary=result.extraction_summary,
    )


def ingest_lanhu_raw_source_in_new_session(
    project_id: int, url: str, *, business_ref_type: str = "", business_ref_id: int | None = None,
    description: str = "",
) -> None:
    """需求上传蓝湖链接后的后台钩子：自带 Session、post-commit、失败不影响主流程。

    仅在 wiki_enabled 时建立 raw source，并绑定业务对象（如 requirement_document）。
    """
    if not settings.wiki_enabled:
        return
    db = SessionLocal()
    try:
        result = asyncio.run(lanhu_provider.extract(url))
        if result.extraction_status in ("auth_failed", "permission_denied", "invalid_url", "failed"):
            return
        content = result.content_md
        if (description or "").strip():
            content = (content + "\n\n## 补充说明\n" + description).strip()
        if not content.strip():
            return
        content_hash = result.content_hash or source_service.content_hash(content)
        raw_source_service.record_raw_source(
            db, project_id=project_id, source_type="lanhu", source_ref=url,
            title=result.module_name or "蓝湖需求", content_md=content,
            content_hash=content_hash, immutable_version=result.immutable_version,
            business_ref_type=business_ref_type, business_ref_id=business_ref_id,
            metadata={
                "doc_id": result.doc_id, "version_id": result.version_id,
                "page_id": result.page_id, "client_scope": result.client_scope,
            },
        )
        db.commit()
    except Exception:
        logger.exception("ingest_lanhu_raw_source failed: url=%s", url)
        db.rollback()
    finally:
        db.close()
