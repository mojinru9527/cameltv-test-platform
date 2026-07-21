"""向量存储抽象（M2 RAG）—— dev 用 SQLite blob + NumPy 暴力余弦，升 PG 切 pgvector。

分层抽象（见 ADR-0010 D2）：上层（入库管线 / search_service）只依赖 `VectorStore` 接口，
底层实现可从 `SqliteVectorStore` 平滑替换为 pgvector 实现，零改上层。

向量在 embedding_service 侧已 L2 归一化 → 余弦相似度退化为点积。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeVector

logger = logging.getLogger("knowledge.vector_store")


@dataclass
class VectorSearchResult:
    chunk_id: int
    score: float


class VectorStore(ABC):
    """向量存储接口。所有实现须保证 chunk_id 维度 1:1（upsert 覆盖）。"""

    @abstractmethod
    def upsert(self, db: Session, *, chunk_id: int, project_id: int, model: str, dim: int, vec) -> int:
        """写入/覆盖某 chunk 的向量，返回向量行 id。"""

    @abstractmethod
    def delete_by_chunk(self, db: Session, chunk_id: int) -> int:
        """删除某 chunk 的向量（chunk 被弃用/删除时清理）。返回删除行数。"""

    @abstractmethod
    def deactivate_project(self, db: Session, project_id: int) -> int:
        """清空某项目的全部向量（项目级隔离/重建）。返回删除行数。"""

    @abstractmethod
    def search(
        self, db: Session, *, project_id: int, query_vec, top_k: int = 8, chunk_type: str | None = None
    ) -> list[VectorSearchResult]:
        """向量检索：项目内、仅 active chunk，按余弦降序返回 top_k。"""


class SqliteVectorStore(VectorStore):
    """SQLite float32 BLOB + NumPy 暴力余弦（语料千级以下足够；见 ADR-0010 风险项）。"""

    def upsert(self, db: Session, *, chunk_id: int, project_id: int, model: str, dim: int, vec) -> int:
        import numpy as np

        blob = np.asarray(vec, dtype=np.float32).tobytes()
        row = db.scalar(select(KnowledgeVector).where(KnowledgeVector.chunk_id == chunk_id))
        if row is not None:
            row.project_id = project_id
            row.model = model
            row.dim = dim
            row.vec = blob
            db.flush()
            return row.id
        row = KnowledgeVector(chunk_id=chunk_id, project_id=project_id, model=model, dim=dim, vec=blob)
        db.add(row)
        db.flush()
        return row.id

    def delete_by_chunk(self, db: Session, chunk_id: int) -> int:
        res = db.execute(delete(KnowledgeVector).where(KnowledgeVector.chunk_id == chunk_id))
        return res.rowcount or 0

    def deactivate_project(self, db: Session, project_id: int) -> int:
        res = db.execute(delete(KnowledgeVector).where(KnowledgeVector.project_id == project_id))
        return res.rowcount or 0

    def search(
        self, db: Session, *, project_id: int, query_vec, top_k: int = 8, chunk_type: str | None = None
    ) -> list[VectorSearchResult]:
        import numpy as np

        q = (
            select(KnowledgeVector.chunk_id, KnowledgeVector.vec)
            .join(KnowledgeChunk, KnowledgeChunk.id == KnowledgeVector.chunk_id)
            .where(
                KnowledgeVector.project_id == project_id,
            )
        )
        if chunk_type:
            q = q.where(KnowledgeChunk.chunk_type == chunk_type)
        rows = db.execute(q).all()
        if not rows:
            return []

        qv = np.asarray(query_vec, dtype=np.float32)
        qn = float(np.linalg.norm(qv))
        if qn == 0.0:
            return []
        qv = qv / qn

        chunk_ids: list[int] = []
        mats: list["np.ndarray"] = []
        for cid, blob in rows:
            v = np.frombuffer(blob, dtype=np.float32)
            if v.shape[0] != qv.shape[0]:
                continue  # 维度不符（模型切换残留），跳过
            chunk_ids.append(int(cid))
            mats.append(v)
        if not mats:
            return []

        matrix = np.vstack(mats)          # (n, dim)，库内向量已归一化
        scores = matrix @ qv              # 余弦（双方已归一化）
        k = min(top_k, len(scores))
        top_idx = np.argpartition(-scores, k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [VectorSearchResult(chunk_id=chunk_ids[i], score=float(scores[i])) for i in top_idx]


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """进程级单例。PG 升级时在此切换实现即可。"""
    global _store
    if _store is None:
        _store = SqliteVectorStore()
    return _store
