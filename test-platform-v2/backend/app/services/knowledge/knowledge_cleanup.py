"""业务数据删除 → 知识源级联（C147-9）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeSource


def mark_business_deleted(
    db: Session,
    *,
    project_id: int,
    source_type: str,
    source_id: int,
) -> int:
    """把关联业务对象的 knowledge_source 标记为 deprecated（软删除同步）。"""
    rows = db.scalars(
        select(KnowledgeSource).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.source_type == source_type,
            KnowledgeSource.source_id == source_id,
            KnowledgeSource.status != "deprecated",
        )
    ).all()
    for row in rows:
        row.status = "deprecated"
    if rows:
        db.flush()
    return len(rows)
