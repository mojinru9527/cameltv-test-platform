"""向量化管线（M2 RAG）—— 将已入库的知识切片嵌入并写入向量库。

设计（见 ADR-0010 D4）：
- **rag_enabled 门控**：开关关闭时直接跳过，零副作用。
- **后 M1-commit、独立事务**：在 M1 切片已提交后，用**独立 Session** 嵌入回填；
  任何嵌入失败都不会回滚 M1 数据，也不抛异常打断主流程。
- **幂等**：只处理 `embedding_id == ""` 的 active 切片；重复调用不重复嵌入。
- 供入库 hook 与 `/knowledge/reembed`（Slice 3）复用。
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeChunk
from app.services.knowledge.embedding_service import embedding_service
from app.services.knowledge.vector_store import get_vector_store

logger = logging.getLogger("knowledge.vectorize")


def _embed_and_store(db: Session, chunks: list[KnowledgeChunk]) -> int:
    """在给定 Session 内嵌入并写向量（不管理 Session、由调用方 commit）。返回成功数。"""
    if not chunks:
        return 0
    vectors = embedding_service.embed([c.content or "" for c in chunks])
    if vectors is None:
        return 0
    store = get_vector_store()
    done = 0
    for chunk, vec in zip(chunks, vectors):
        vid = store.upsert(
            db,
            chunk_id=chunk.id,
            project_id=chunk.project_id,
            model=embedding_service.model_name,
            dim=embedding_service.dim,
            vec=vec,
        )
        chunk.embedding_id = str(vid)
        done += 1
    db.flush()
    return done


def embed_pending_chunks_in_new_session(
    project_id: int, source_id: int | None = None, limit: int | None = None
) -> dict:
    """嵌入项目内待处理切片（active 且 embedding_id 为空）。独立 Session、失败静默。

    - source_id 给定时仅处理该源的切片（入库 hook 用）；否则全项目（回填用）。
    - 返回 {"embedded": n, "skipped": m}；rag 关闭或模型不可用时 embedded=0。
    """
    if not settings.rag_enabled:
        return {"embedded": 0, "skipped": 0, "reason": "rag_disabled"}
    if not embedding_service.available():
        return {"embedded": 0, "skipped": 0, "reason": "model_unavailable"}

    batch = limit or settings.embedding_batch_size
    db = SessionLocal()
    try:
        embedded_total = 0
        scanned_total = 0
        while True:
            q = select(KnowledgeChunk).where(
                KnowledgeChunk.project_id == project_id,
                KnowledgeChunk.status == "active",
                KnowledgeChunk.embedding_id == "",
            )
            if source_id is not None:
                q = q.where(KnowledgeChunk.source_id == source_id)
            q = q.order_by(KnowledgeChunk.id.asc()).limit(batch)
            chunks = list(db.scalars(q).all())
            if not chunks:
                break
            scanned_total += len(chunks)
            embedded_total += _embed_and_store(db, chunks)
            db.commit()
            if len(chunks) < batch:
                break
        return {"embedded": embedded_total, "skipped": scanned_total - embedded_total}
    except Exception:  # noqa: BLE001 — 嵌入永不影响主流程/已提交的 M1 数据
        logger.exception("embed pending chunks failed project_id=%s source_id=%s", project_id, source_id)
        db.rollback()
        return {"embedded": 0, "skipped": 0, "reason": "error"}
    finally:
        db.close()
