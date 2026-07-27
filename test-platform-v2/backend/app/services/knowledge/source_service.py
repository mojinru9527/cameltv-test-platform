"""知识源服务 —— 入库（去重）、列表、详情、废弃、验证。

约定：本模块函数只 `db.flush()`，由调用方（ingest_service 自带 Session）负责 commit。
去重键：(project_id, source_type, source_id, content_hash)。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeSource
from app.services.knowledge.sanitize import sanitize


def content_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def record_source(
    db: Session,
    *,
    project_id: int,
    source_type: str,
    source_id: int | None,
    title: str,
    source_ref: str = "",
    raw_content: str,
    version: str = "",
    iteration_id: int | None = None,
    metadata: dict | None = None,
) -> KnowledgeSource | None:
    """写入一条知识源；若同内容已存在则跳过并返回 None（幂等去重）。

    - `title` / `source_ref` 在此统一脱敏（防御纵深：即使调用方漏脱敏，敏感值也不入库）；
    - 同 (project_id, source_type, source_id) 的历史源在写入新版本时置为 `superseded`，
      避免实体被反复编辑后累积僵尸活跃源（source_id 为空的手工源不做 supersede）。
    """
    chash = content_hash(raw_content)
    exists = db.scalar(
        select(KnowledgeSource.id).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.source_type == source_type,
            KnowledgeSource.source_id == source_id,
            KnowledgeSource.content_hash == chash,
        )
    )
    if exists:
        return None

    # supersede：内容已变更（新 hash）时，把该实体的旧活跃源及其切片标记为被取代
    if source_id is not None:
        from app.models.knowledge import KnowledgeChunk

        old_ids = list(
            db.scalars(
                select(KnowledgeSource.id).where(
                    KnowledgeSource.project_id == project_id,
                    KnowledgeSource.source_type == source_type,
                    KnowledgeSource.source_id == source_id,
                    KnowledgeSource.status == "parsed",
                )
            ).all()
        )
        if old_ids:
            db.execute(
                update(KnowledgeChunk)
                .where(KnowledgeChunk.source_id.in_(old_ids), KnowledgeChunk.status == "active")
                .values(status="superseded")
            )
            db.execute(
                update(KnowledgeSource)
                .where(KnowledgeSource.id.in_(old_ids))
                .values(status="superseded")
            )

    row = KnowledgeSource(
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        title=sanitize(title)[:500],
        source_ref=sanitize(source_ref)[:500],
        content_hash=chash,
        version=version or "",
        iteration_id=iteration_id,
        status="parsed",
        raw_content=raw_content or "",
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row


def list_sources(
    db: Session,
    project_id: int,
    *,
    source_type: str | None = None,
    para_category: str | None = None,
    knowledge_domain: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeSource], int]:
    stmt = select(KnowledgeSource).where(KnowledgeSource.project_id == project_id)
    cnt = select(func.count(KnowledgeSource.id)).where(KnowledgeSource.project_id == project_id)
    if source_type:
        stmt = stmt.where(KnowledgeSource.source_type == source_type)
        cnt = cnt.where(KnowledgeSource.source_type == source_type)
    if para_category:
        stmt = stmt.where(KnowledgeSource.para_category == para_category)
        cnt = cnt.where(KnowledgeSource.para_category == para_category)
    if knowledge_domain:
        stmt = stmt.where(KnowledgeSource.knowledge_domain == knowledge_domain)
        cnt = cnt.where(KnowledgeSource.knowledge_domain == knowledge_domain)
    if status:
        stmt = stmt.where(KnowledgeSource.status == status)
        cnt = cnt.where(KnowledgeSource.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(KnowledgeSource.title.like(kw))
        cnt = cnt.where(KnowledgeSource.title.like(kw))

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(KnowledgeSource.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_source(db: Session, source_pk: int, project_id: int) -> KnowledgeSource | None:
    row = db.get(KnowledgeSource, source_pk)
    if not row or row.project_id != project_id:
        return None
    return row


def verify_source(db: Session, source_pk: int, project_id: int) -> KnowledgeSource | None:
    """验证知识源：设置 last_verified_at = now()，freshness_score = 1.0。"""

    row = get_source(db, source_pk, project_id)
    if not row:
        return None
    row.last_verified_at = datetime.now()
    row.freshness_score = 1.0
    db.flush()
    return row


def classify_source(
    db: Session, source_pk: int, project_id: int,
    *, para_category: str | None = None, knowledge_domain: str | None = None,
) -> KnowledgeSource | None:
    """更新知识源的 PARA 分类 / 知识域。"""
    row = get_source(db, source_pk, project_id)
    if not row:
        return None
    if para_category is not None:
        row.para_category = para_category
    if knowledge_domain is not None:
        row.knowledge_domain = knowledge_domain
    db.flush()
    return row


def decay_freshness_in_new_session() -> dict:
    """保鲜自动退化 + 自动归档（独立 Session，供定时任务调用）。

    规则：
    - 所有 status='parsed' 且 freshness_score > 0.1 的源，每天递减 0.01
    - freshness_score < 0.2 且 last_verified_at 距今 > 90 天的源 → status='deprecated'
    - freshness_score < 0.2 且 last_verified_at 为空的源 → status='deprecated'（从未验证过）
    """
    from datetime import timedelta
    from app.core.db import SessionLocal
    from sqlalchemy import update

    db = SessionLocal()
    try:
        now = datetime.now()
        threshold = now - timedelta(days=90)

        # 1) 保鲜退化：所有活跃源每天 -0.01
        result_decay = db.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.status == "parsed",
                KnowledgeSource.freshness_score > 0.1,
            )
            .values(freshness_score=KnowledgeSource.freshness_score - 0.01)
        )

        # 2) 自动归档：freshness < 0.2 且长期未验证
        result_archive_old = db.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.status == "parsed",
                KnowledgeSource.freshness_score < 0.2,
                KnowledgeSource.last_verified_at.isnot(None),
                KnowledgeSource.last_verified_at < threshold,
            )
            .values(status="deprecated")
        )

        # 3) 从未验证且保鲜过低
        result_archive_never = db.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.status == "parsed",
                KnowledgeSource.freshness_score < 0.2,
                KnowledgeSource.last_verified_at.is_(None),
            )
            .values(status="deprecated")
        )

        db.commit()

        return {
            "decayed": result_decay.rowcount,
            "archived_old": result_archive_old.rowcount,
            "archived_never_verified": result_archive_never.rowcount,
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def deprecate_source(db: Session, source_pk: int, project_id: int) -> bool:
    """废弃知识源；其切片一并置为 deprecated（不参与默认检索）。"""
    from app.models.knowledge import KnowledgeChunk

    row = get_source(db, source_pk, project_id)
    if not row:
        return False
    row.status = "deprecated"
    for chunk in db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.source_id == row.id)
    ).all():
        chunk.status = "deprecated"
    db.flush()
    return True
