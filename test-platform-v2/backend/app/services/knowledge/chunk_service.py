"""知识切片服务 —— 将知识源切片入库（去重），供 RAG 检索使用（M2 再向量化）。

约定：只 `db.flush()`，由调用方 commit。切片去重键：(source_id, content_hash)。
"""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeSource
from app.services.knowledge.source_service import content_hash

# 粗略 token 估算：中文按字符、英文按 ~4 字符/token，取字符数/2 作近似
_TOKEN_DIVISOR = 2

_NO_ACTIVE_CHUNKS = "当前项目没有可提取的有效知识片段，请先导入并解析知识源"
_NO_ACTIVE_SOURCE_CHUNKS = "指定知识源没有可提取的有效知识片段"


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // _TOKEN_DIVISOR)


def slice_text(text: str, *, max_chars: int = 1200) -> list[str]:
    """朴素切片：先按空行分段，再对超长段落按 max_chars 硬切。"""
    text = (text or "").strip()
    if not text:
        return []
    parts: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 2 <= max_chars:
            buf = f"{buf}\n\n{para}" if buf else para
        else:
            if buf:
                parts.append(buf)
            # 段落自身超长 → 硬切
            while len(para) > max_chars:
                parts.append(para[:max_chars])
                para = para[max_chars:]
            buf = para
    if buf:
        parts.append(buf)
    return parts


def make_chunks(db: Session, source: KnowledgeSource, chunks: list[dict]) -> int:
    """写入切片，按 (source_id, content_hash) 去重，返回新增数量。

    每个 chunk dict: {chunk_type, title, content, tags?}
    """
    created = 0
    for c in chunks:
        content = (c.get("content") or "").strip()
        if not content:
            continue
        chash = content_hash(content)
        dup = db.scalar(
            select(KnowledgeChunk.id).where(
                KnowledgeChunk.source_id == source.id,
                KnowledgeChunk.content_hash == chash,
            )
        )
        if dup:
            continue
        db.add(
            KnowledgeChunk(
                project_id=source.project_id,
                source_id=source.id,
                chunk_type=c.get("chunk_type") or "",
                title=(c.get("title") or "")[:500],
                content=content,
                content_hash=chash,
                token_count=estimate_tokens(content),
                embedding_id="",
                tags=json.dumps(c.get("tags") or [], ensure_ascii=False),
                status="active",
            )
        )
        created += 1
    db.flush()
    return created


def list_chunks_by_source(db: Session, source_pk: int) -> list[KnowledgeChunk]:
    return list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.source_id == source_pk)
            .order_by(KnowledgeChunk.id.asc())
        ).all()
    )


def get_chunk(db: Session, chunk_pk: int, project_id: int) -> KnowledgeChunk | None:
    row = db.get(KnowledgeChunk, chunk_pk)
    if not row or row.project_id != project_id:
        return None
    return row


def has_active_chunks(
    db: Session,
    project_id: int,
    source_id: int | None = None,
) -> tuple[bool, str]:
    """检查项目/知识源是否存在可提取的有效切片（Batch 181 P2-10 收敛）。

    保留原路由 _graph_extract_availability 的错误文案语义。
    """
    stmt = select(KnowledgeChunk.id).where(
        KnowledgeChunk.project_id == project_id,
        KnowledgeChunk.is_deleted.is_(False),
    )
    if source_id is not None:
        stmt = stmt.where(KnowledgeChunk.source_id == source_id)
    if db.scalar(stmt.limit(1)) is not None:
        return True, ""
    return False, _NO_ACTIVE_SOURCE_CHUNKS if source_id is not None else _NO_ACTIVE_CHUNKS


def count_chunks(db: Session, project_id: int, *, embedded_only: bool = False) -> int:
    """统计项目内未删除切片数；embedded_only=True 仅统计已嵌入（embedding_id != ""）的切片。"""
    stmt = select(func.count(KnowledgeChunk.id)).where(
        KnowledgeChunk.project_id == project_id,
        KnowledgeChunk.is_deleted.is_(False),
    )
    if embedded_only:
        stmt = stmt.where(KnowledgeChunk.embedding_id != "")
    return db.scalar(stmt) or 0


def count_pending_embedding_chunks(db: Session, project_id: int) -> int:
    """统计项目内未嵌入（embedding_id == ""）的未删除切片数（reembed 扫描基数）。"""
    stmt = select(func.count(KnowledgeChunk.id)).where(
        KnowledgeChunk.project_id == project_id,
        KnowledgeChunk.is_deleted.is_(False),
        KnowledgeChunk.embedding_id == "",
    )
    return db.scalar(stmt) or 0
