"""知识切片服务 —— 将知识源切片入库（去重），供 RAG 检索使用（M2 再向量化）。

约定：只 `db.flush()`，由调用方 commit。切片去重键：(source_id, content_hash)。
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeSource
from app.services.knowledge.source_service import content_hash

# 粗略 token 估算：中文按字符、英文按 ~4 字符/token，取字符数/2 作近似
_TOKEN_DIVISOR = 2


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
