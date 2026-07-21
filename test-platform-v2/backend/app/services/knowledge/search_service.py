"""混合检索服务（M2 RAG）—— 关键词 + 向量，RRF 融合排序（见 ADR-0010 D3）。

- 关键词：SQLite LIKE（CJK 二元组保召回 + Python 侧计分；FTS5 为后续优化）。
- 向量：委托 vector_store（NumPy 余弦），query 侧经 embedding_service 加检索前缀嵌入。
- 融合：Reciprocal Rank Fusion（对量纲鲁棒，无需归一两路分数）。
- 治理：仅项目内、仅 status="active" 切片（vector_store 与 keyword 均已过滤）。

mode: "hybrid"（默认）| "keyword" | "vector"，便于对比与降级（模型不可用时可纯关键词）。
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeSource
from app.services.knowledge.embedding_service import embedding_service
from app.services.knowledge.sanitize import sanitize
from app.services.knowledge.vector_store import get_vector_store

logger = logging.getLogger("knowledge.search")

_RRF_K = 60          # RRF 常数（Cormack SIGIR'09 推荐 60）
_CANDIDATE_MULT = 3  # 每路召回 top_k*mult 个候选参与融合
_SNIPPET_LEN = 160
_CJK_RE = re.compile(r"[一-鿿]")


@dataclass
class SearchHit:
    chunk_id: int
    chunk_type: str
    title: str
    snippet: str
    score: float
    source_id: int
    source_name: str


def _tokenize(query: str) -> list[str]:
    """中英混排分词，服务于 LIKE 召回。

    中文无空格：对 CJK 段既保留整段（强信号），又生成字符二元组（bigram）以保证召回
    （FTS5 未建表时的经典 CJK LIKE 方案）。英文/数字段按原样保留。
    """
    segs = re.split(r"[\s,，。;；:：/\\|、()（）\[\]{}]+", (query or "").strip())
    terms: list[str] = []
    for seg in segs:
        if not seg:
            continue
        if _CJK_RE.search(seg):
            if len(seg) >= 2:
                terms.append(seg)  # 整段：最强信号
                for i in range(len(seg) - 1):
                    terms.append(seg[i:i + 2])  # 字符二元组：保召回
            else:
                terms.append(seg)
        else:
            terms.append(seg)
    # 去重保序，限量
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:32]


def _keyword_search(
    db: Session, project_id: int, query: str, limit: int, chunk_type: str | None = None
) -> list[int]:
    """LIKE 召回 + Python 计分，返回按相关度降序的 chunk_id 列表。"""
    terms = _tokenize(query)
    if not terms:
        return []
    base = select(
        KnowledgeChunk.id, KnowledgeChunk.title, KnowledgeChunk.content
    ).where(
        KnowledgeChunk.project_id == project_id,
    )
    if chunk_type:
        base = base.where(KnowledgeChunk.chunk_type == chunk_type)
    conds = []
    for t in terms:
        like = f"%{t}%"
        conds.append(KnowledgeChunk.title.like(like))
        conds.append(KnowledgeChunk.content.like(like))
    rows = db.execute(base.where(or_(*conds)).limit(500)).all()
    if not rows:
        return []
    scored: list[tuple[float, int]] = []
    for cid, title, content in rows:
        title_l = (title or "").lower()
        content_l = (content or "").lower()
        score = 0.0
        for t in terms:
            tl = t.lower()
            # 长词/整段权重更高（bigram≈1，4+字整段≈2），避免二元组噪声盖过完整短语命中
            w = min(len(t), 4) / 2.0
            if tl in title_l:
                score += 2.0 * w            # 标题命中权重更高
            if tl in content_l:
                score += 1.0 * w
        if score > 0:
            scored.append((score, cid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [cid for _, cid in scored[:limit]]


def _vector_search(
    db: Session, project_id: int, query: str, limit: int, chunk_type: str | None = None
) -> list[int]:
    """向量召回，返回按余弦降序的 chunk_id 列表（模型不可用时返回空，自动降级为纯关键词）。"""
    qv = embedding_service.embed_query(query)
    if qv is None:
        return []
    results = get_vector_store().search(
        db, project_id=project_id, query_vec=qv, top_k=limit, chunk_type=chunk_type
    )
    return [r.chunk_id for r in results]


def _rrf_fuse(rankings: list[list[int]], rrf_k: int = _RRF_K) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion：score(cid) = Σ 1/(rrf_k + rank)。返回 (chunk_id, score) 降序。"""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] += 1.0 / (rrf_k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def _make_snippet(content: str, terms: list[str]) -> str:
    content = (content or "").replace("\n", " ").strip()
    if not content:
        return ""
    low = content.lower()
    pos = -1
    for t in terms:
        i = low.find(t.lower())
        if i >= 0:
            pos = i
            break
    if pos < 0:
        return content[:_SNIPPET_LEN] + ("…" if len(content) > _SNIPPET_LEN else "")
    start = max(0, pos - 30)
    end = min(len(content), start + _SNIPPET_LEN)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{content[start:end]}{suffix}"


def _hydrate(db: Session, ranked: list[tuple[int, float]], query: str) -> list[SearchHit]:
    if not ranked:
        return []
    ids = [cid for cid, _ in ranked]
    chunks = {c.id: c for c in db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(ids))).all()}
    source_ids = {c.source_id for c in chunks.values()}
    sources = {
        s.id: s.title
        for s in db.scalars(select(KnowledgeSource).where(KnowledgeSource.id.in_(source_ids))).all()
    }
    terms = _tokenize(query)
    hits: list[SearchHit] = []
    for cid, score in ranked:
        c = chunks.get(cid)
        if not c:
            continue
        hits.append(
            SearchHit(
                chunk_id=c.id,
                chunk_type=c.chunk_type,
                title=c.title,
                snippet=_make_snippet(c.content, terms),
                score=round(float(score), 6),
                source_id=c.source_id,
                source_name=sources.get(c.source_id, ""),
            )
        )
    return hits


def hybrid_search(
    db: Session,
    *,
    project_id: int,
    query: str,
    top_k: int = 8,
    chunk_type: str | None = None,
    mode: str = "hybrid",
) -> list[SearchHit]:
    """检索入口。query 先脱敏（避免把敏感串带入检索日志/嵌入）。"""
    query = sanitize((query or "").strip())
    if not query:
        return []
    top_k = max(1, min(top_k, 50))
    cand = top_k * _CANDIDATE_MULT

    if mode == "keyword":
        ranked = [
            (cid, 1.0 / (_RRF_K + i + 1))
            for i, cid in enumerate(_keyword_search(db, project_id, query, cand, chunk_type))
        ]
    elif mode == "vector":
        ranked = [
            (cid, 1.0 / (_RRF_K + i + 1))
            for i, cid in enumerate(_vector_search(db, project_id, query, cand, chunk_type))
        ]
    else:  # hybrid
        kw = _keyword_search(db, project_id, query, cand, chunk_type)
        vec = _vector_search(db, project_id, query, cand, chunk_type)
        ranked = _rrf_fuse([kw, vec])

    return _hydrate(db, ranked[:top_k], query)
