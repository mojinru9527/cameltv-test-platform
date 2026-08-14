"""业务数据删除 → 知识源级联（C147-9 / FIX-173-P1-04）。"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeSource, KnowledgeVector


def mark_business_deleted(
    db: Session,
    *,
    project_id: int,
    source_type: str,
    source_id: int,
) -> int:
    """业务对象删除时级联清理其知识源、切片与向量（硬删，Batch 177）。

    Batch 177（FIX-173-P1-04）：此前仅标记 deprecated，导致已删缺陷的知识切片
    仍在知识中心「项目知识」可见（source id=113 残留实例）。业务对象已删除，
    其知识切片无保留价值，改为硬删源+切片+向量，消除用户可见残留。
    返回删除的知识源数量。
    """
    rows = db.scalars(
        select(KnowledgeSource).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.source_type == source_type,
            KnowledgeSource.source_id == source_id,
        )
    ).all()
    removed = 0
    for row in rows:
        chunk_ids = list(
            db.scalars(
                select(KnowledgeChunk.id).where(KnowledgeChunk.source_id == row.id)
            ).all()
        )
        if chunk_ids:
            db.execute(
                delete(KnowledgeVector).where(KnowledgeVector.chunk_id.in_(chunk_ids))
            )
        db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == row.id)
        )
        db.delete(row)
        removed += 1
    if removed:
        db.flush()
    return removed
