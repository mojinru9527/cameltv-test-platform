"""知识源服务 —— 入库（去重）、列表、详情、废弃、验证。

约定：本模块函数只 `db.flush()`，由调用方（ingest_service 自带 Session）负责 commit。
去重键：(project_id, source_type, source_id, content_hash)。
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path

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
                .where(KnowledgeChunk.source_id.in_(old_ids), KnowledgeChunk.is_deleted.is_(False))
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
    # Batch 181（FIX-173-P2-08）：删除语义统一 is_deleted；默认列表隐藏已删源。
    # 显式传 status 筛选时尊重调用方意图（如管理视图查看历史 deprecated 源）。
    if not status:
        stmt = stmt.where(KnowledgeSource.is_deleted.is_(False))
        cnt = cnt.where(KnowledgeSource.is_deleted.is_(False))
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
    - freshness_score < 0.2 且 last_verified_at 距今 > 90 天的源 → is_deleted=True（Batch 181 统一语义）
    - freshness_score < 0.2 且 last_verified_at 为空的源 → is_deleted=True（从未验证过）
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
        #    Batch 181：过滤语义写 is_deleted=True；status 保留 deprecated 作 UI 展示值
        result_archive_old = db.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.status == "parsed",
                KnowledgeSource.freshness_score < 0.2,
                KnowledgeSource.last_verified_at.isnot(None),
                KnowledgeSource.last_verified_at < threshold,
            )
            .values(is_deleted=True, status="deprecated")
        )

        # 3) 从未验证且保鲜过低
        result_archive_never = db.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.status == "parsed",
                KnowledgeSource.freshness_score < 0.2,
                KnowledgeSource.last_verified_at.is_(None),
            )
            .values(is_deleted=True, status="deprecated")
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
    """废弃知识源；其切片一并标记删除。

    Batch 181：过滤语义统一 is_deleted=True；status 保留 deprecated 作 UI 展示值
    （前端按 status 渲染「已废弃」徽标，历史值与新值行为一致）。
    """
    from app.models.knowledge import KnowledgeChunk

    row = get_source(db, source_pk, project_id)
    if not row:
        return False
    row.is_deleted = True
    row.status = "deprecated"
    for chunk in db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.source_id == row.id)
    ).all():
        chunk.is_deleted = True
        chunk.status = "deprecated"
    db.flush()
    return True


def get_knowledge_overview(db: Session, project_id: int) -> dict:
    """知识中心概览聚合（Batch 181 P2-10：路由层 ORM 收敛）。

    返回 overview 所需的全部 DB 派生字段；RAG 开关/嵌入模型等 settings
    派生值由路由层组装（不在本函数内读 settings）。
    """
    from app.models.knowledge import (
        AgentRun, AiArtifact, KnowledgeChunk, KnowledgeEntity, KnowledgeRelation,
    )

    pid = project_id

    def _count(model, *conds) -> int:
        stmt = select(func.count(model.id)).where(model.project_id == pid, *conds)
        return db.scalar(stmt) or 0

    source_count = _count(KnowledgeSource, KnowledgeSource.is_deleted.is_(False))
    chunk_count = _count(KnowledgeChunk, KnowledgeChunk.is_deleted.is_(False))
    entity_count = _count(KnowledgeEntity)
    pending_artifacts = _count(AiArtifact, AiArtifact.review_status == "pending")
    deprecated_sources = _count(KnowledgeSource, KnowledgeSource.is_deleted.is_(True))

    # 孤儿切片：引用了不存在知识源的切片
    sourceless = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.project_id == pid,
            KnowledgeChunk.source_id.notin_(select(KnowledgeSource.id)),
        )
    ) or 0

    recent = db.scalars(
        select(KnowledgeSource)
        .where(KnowledgeSource.project_id == pid)
        .order_by(KnowledgeSource.id.desc())
        .limit(5)
    ).all()

    # M3: 关系健康指标
    low_confidence_relations = _count(KnowledgeRelation, KnowledgeRelation.confidence < 0.5)
    unreviewed_relations = _count(KnowledgeRelation, KnowledgeRelation.review_status == "pending")

    # M4: Agent 执行指标
    agent_total_runs = _count(AgentRun)
    agent_avg_duration = db.scalar(
        select(func.avg(AgentRun.duration_ms)).where(
            AgentRun.project_id == pid,
            AgentRun.status == "success",
            AgentRun.duration_ms > 0,
        )
    ) or 0
    # 采纳率 = approved / (approved + rejected)
    approved_count = _count(AiArtifact, AiArtifact.review_status == "approved")
    rejected_count = _count(AiArtifact, AiArtifact.review_status == "rejected")
    total_reviewed = approved_count + rejected_count
    agent_approval_rate = approved_count / total_reviewed if total_reviewed > 0 else 0.0

    # M2 RAG: embedding 覆盖率（已嵌入切片数）
    embedded_chunks = _count(
        KnowledgeChunk, KnowledgeChunk.is_deleted.is_(False), KnowledgeChunk.embedding_id != ""
    )

    return {
        "source_count": source_count,
        "chunk_count": chunk_count,
        "entity_count": entity_count,
        "pending_artifacts": pending_artifacts,
        "deprecated_sources": deprecated_sources,
        "sourceless": sourceless,
        "recent_sources": list(recent),
        "low_confidence_relations": low_confidence_relations,
        "unreviewed_relations": unreviewed_relations,
        "agent_total_runs": agent_total_runs,
        "agent_avg_duration": agent_avg_duration,
        "agent_approval_rate": agent_approval_rate,
        "embedded_chunks": embedded_chunks,
    }


def _design_storage_base() -> Path:
    """需求设计稿图片存储根目录（与路由层 _design_storage_base 公式一致）。"""
    from app.core.config import settings

    base = Path(settings.lanhu_evidence_storage_dir) if settings.lanhu_evidence_storage_dir else Path(__file__).resolve().parent.parent.parent.parent / "storage"
    return base / "requirement-design"


def import_design_assets(db: Session, project_id: int, sources: list) -> dict:
    """需求/设计稿入库为知识源 + 切片，幂等（按 content_hash 去重）。

    Batch 181 P2-10：原路由层直连 ORM 的逻辑整体收敛至此；图片落盘、
    KnowledgeSource/KnowledgeChunk 写入均在本函数内完成，commit 由路由层保留。
    """
    import hashlib

    from app.models.knowledge import KnowledgeChunk

    pid = project_id
    created_s = skipped_s = created_c = saved_i = 0
    for src in sources:
        text = src.text or ""
        chash = hashlib.sha1(f"{src.source_ref}|{src.title}|{text}".encode("utf-8")).hexdigest()[:32]
        exists = db.scalar(
            select(KnowledgeSource.id).where(
                KnowledgeSource.project_id == pid,
                KnowledgeSource.content_hash == chash,
            )
        )
        if exists:
            skipped_s += 1
            continue
        row = KnowledgeSource(
            project_id=pid,
            source_type="requirement",
            title=src.title,
            source_ref=src.source_ref,
            content_hash=chash,
            raw_content=text,
            para_category="project",
            knowledge_domain="project",
            freshness_score=1.0,
            metadata_json=json.dumps({"page": src.title, "source_ref": src.source_ref, "image_count": len(src.images)}, ensure_ascii=False),
        )
        db.add(row)
        db.flush()
        created_s += 1

        img_urls: list[str] = []
        if src.images:
            img_dir = _design_storage_base() / str(row.id)
            img_dir.mkdir(parents=True, exist_ok=True)
            for img in src.images:
                if not img.filename or not img.base64:
                    continue
                name = Path(img.filename).name
                try:
                    data = base64.b64decode(img.base64)
                except Exception:
                    continue
                if len(data) > 6 * 1024 * 1024:
                    continue
                (img_dir / name).write_bytes(data)
                img_urls.append(f"/api/v1/knowledge/design-assets/{row.id}/{name}")
                saved_i += 1
        if img_urls:
            row.metadata_json = json.dumps({"page": src.title, "source_ref": src.source_ref, "image_count": len(src.images), "images": img_urls}, ensure_ascii=False)

        if text:
            db.add(KnowledgeChunk(
                project_id=pid,
                source_id=row.id,
                chunk_type="requirement_rule",
                title=src.title,
                content=text,
                content_hash=hashlib.sha1(text.encode("utf-8")).hexdigest()[:32],
                token_count=max(1, len(text) // 4),
                status="active",
            ))
            created_c += 1

    db.flush()
    return {
        "created_sources": created_s,
        "skipped_sources": skipped_s,
        "created_chunks": created_c,
        "saved_images": saved_i,
    }
