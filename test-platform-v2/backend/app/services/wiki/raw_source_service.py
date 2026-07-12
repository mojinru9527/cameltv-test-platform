"""Wiki Raw Source 服务 —— 蓝湖等原始来源入库（去重 + supersede）、列表、详情。

约定同 knowledge/source_service：本模块函数只 `db.flush()`，由调用方负责 commit。
去重键：(project_id, immutable_version, content_hash)。内容变更（新 hash）时把同
immutable_version 的旧活跃源置为 superseded；原始来源不可被 LLM 改写。
"""
from __future__ import annotations

import json

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.wiki import WikiRawSource
from app.services.knowledge.sanitize import sanitize


def record_raw_source(
    db: Session,
    *,
    project_id: int,
    source_type: str = "lanhu",
    source_ref: str = "",
    title: str,
    content_md: str,
    content_hash: str = "",
    immutable_version: str = "",
    business_ref_type: str = "",
    business_ref_id: int | None = None,
    knowledge_source_id: int | None = None,
    metadata: dict | None = None,
) -> WikiRawSource | None:
    """写入一条 raw source；若同 (immutable_version, content_hash) 已存在则跳过并返回 None。

    - `title` / `source_ref` 统一脱敏（防御纵深）；`content_md` 走 sanitize 脱敏。
    - immutable_version 相同但 content_hash 变化 → 旧活跃源置 superseded，写入新版本。
    - immutable_version 为空时退化为按 content_hash 去重（仅同 project + hash 唯一）。
    """
    key = immutable_version or content_hash
    exists = db.scalar(
        select(WikiRawSource.id).where(
            WikiRawSource.project_id == project_id,
            WikiRawSource.immutable_version == (immutable_version or ""),
            WikiRawSource.content_hash == content_hash,
        )
    )
    if exists:
        return None

    # supersede：同 immutable_version 的旧活跃源（内容已变更）标记被取代
    if immutable_version:
        db.execute(
            update(WikiRawSource)
            .where(
                WikiRawSource.project_id == project_id,
                WikiRawSource.immutable_version == immutable_version,
                WikiRawSource.status == "active",
            )
            .values(status="superseded")
        )

    row = WikiRawSource(
        project_id=project_id,
        source_type=source_type,
        source_ref=sanitize(source_ref)[:500],
        business_ref_type=business_ref_type,
        business_ref_id=business_ref_id,
        knowledge_source_id=knowledge_source_id,
        title=sanitize(title)[:500],
        content_md=sanitize(content_md or ""),
        content_hash=content_hash,
        immutable_version=immutable_version or "",
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def list_raw_sources(
    db: Session,
    project_id: int,
    *,
    source_type: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WikiRawSource], int]:
    stmt = select(WikiRawSource).where(WikiRawSource.project_id == project_id)
    cnt = select(func.count(WikiRawSource.id)).where(WikiRawSource.project_id == project_id)
    if source_type:
        stmt = stmt.where(WikiRawSource.source_type == source_type)
        cnt = cnt.where(WikiRawSource.source_type == source_type)
    if status:
        stmt = stmt.where(WikiRawSource.status == status)
        cnt = cnt.where(WikiRawSource.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(WikiRawSource.title.like(kw))
        cnt = cnt.where(WikiRawSource.title.like(kw))

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(WikiRawSource.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_raw_source(db: Session, raw_source_pk: int, project_id: int) -> WikiRawSource | None:
    row = db.get(WikiRawSource, raw_source_pk)
    if not row or row.project_id != project_id:
        return None
    return row
