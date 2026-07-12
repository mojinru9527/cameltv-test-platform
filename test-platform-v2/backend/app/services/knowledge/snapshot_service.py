"""迭代快照服务（M6）—— 迭代知识包归档 + 跨迭代对比。

设计：
- 快照仅在迭代关闭时创建（幂等：已存在的 snapshot_type 覆盖）
- 快照内容：entity/relation/chunk 计数 + 质量指标
- 跨迭代对比：计算增量/减量/变化率
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeEntity,
    KnowledgeIteration,
    KnowledgeRelation,
    KnowledgeSnapshot,
    KnowledgeSource,
)

logger = logging.getLogger("knowledge.snapshot")

# 快照类型常量
SNAPSHOT_ENTITY = "entity"
SNAPSHOT_RELATION = "relation"
SNAPSHOT_CHUNK = "chunk"
SNAPSHOT_STATS = "stats"


# ── 迭代 CRUD ──

def create_iteration(
    db: Session,
    project_id: int,
    iteration_name: str,
    version: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    description: str = "",
) -> KnowledgeIteration:
    """创建新迭代。"""
    it = KnowledgeIteration(
        project_id=project_id,
        iteration_name=iteration_name,
        version=version,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        description=description,
        status="active",
    )
    db.add(it)
    db.flush()
    return it


def close_iteration(db: Session, iteration_id: int, project_id: int) -> KnowledgeIteration | None:
    """关闭迭代，自动创建快照。"""
    it = db.get(KnowledgeIteration, iteration_id)
    if not it or it.project_id != project_id:
        return None
    if it.status != "active":
        return None

    it.status = "closed"
    it.end_date = datetime.now()
    db.flush()

    # 自动创建快照
    _create_all_snapshots_in_session(db, iteration_id, project_id)

    return it


def list_iterations(
    db: Session,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeIteration], int]:
    """列出迭代。"""
    stmt = select(KnowledgeIteration).where(KnowledgeIteration.project_id == project_id)
    cnt = select(func.count(KnowledgeIteration.id)).where(KnowledgeIteration.project_id == project_id)
    if status:
        stmt = stmt.where(KnowledgeIteration.status == status)
        cnt = cnt.where(KnowledgeIteration.status == status)

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(KnowledgeIteration.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_iteration(db: Session, iteration_id: int, project_id: int) -> KnowledgeIteration | None:
    it = db.get(KnowledgeIteration, iteration_id)
    if not it or it.project_id != project_id:
        return None
    return it


# ── 快照 ──

def _create_all_snapshots_in_session(db: Session, iteration_id: int, project_id: int) -> None:
    """在给定 Session 中创建所有类型的快照（幂等：覆盖已有）。"""
    # Entity 快照
    _upsert_snapshot(db, iteration_id, SNAPSHOT_ENTITY, _collect_entity_snapshot(db, project_id))

    # Relation 快照
    _upsert_snapshot(db, iteration_id, SNAPSHOT_RELATION, _collect_relation_snapshot(db, project_id))

    # Chunk 快照
    _upsert_snapshot(db, iteration_id, SNAPSHOT_CHUNK, _collect_chunk_snapshot(db, project_id))

    # Stats 快照（汇总）
    _upsert_snapshot(db, iteration_id, SNAPSHOT_STATS, _collect_stats_snapshot(db, project_id))

    logger.info("Snapshots created for iteration %s", iteration_id)


def _upsert_snapshot(db: Session, iteration_id: int, snapshot_type: str, data: dict) -> None:
    """幂等写入快照：存在则更新，不存在则创建。"""
    existing = db.scalar(
        select(KnowledgeSnapshot).where(
            KnowledgeSnapshot.iteration_id == iteration_id,
            KnowledgeSnapshot.snapshot_type == snapshot_type,
        )
    )
    if existing:
        existing.data_json = json.dumps(data, ensure_ascii=False)
    else:
        snap = KnowledgeSnapshot(
            iteration_id=iteration_id,
            snapshot_type=snapshot_type,
            data_json=json.dumps(data, ensure_ascii=False),
        )
        db.add(snap)


def _collect_entity_snapshot(db: Session, project_id: int) -> dict:
    """收集实体维度的快照数据。"""
    counts = {}
    types = ["api", "field", "requirement", "test_case", "defect", "module", "project"]
    for t in types:
        counts[t] = db.scalar(
            select(func.count(KnowledgeEntity.id)).where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_type == t,
            )
        ) or 0

    total = sum(counts.values())
    avg_confidence = db.scalar(
        select(func.avg(KnowledgeEntity.confidence)).where(
            KnowledgeEntity.project_id == project_id,
        )
    ) or 0

    return {
        "total": total,
        "by_type": counts,
        "avg_confidence": round(float(avg_confidence), 4),
    }


def _collect_relation_snapshot(db: Session, project_id: int) -> dict:
    """收集关系维度的快照数据。"""
    counts = {}
    types = ["contains", "affects", "covers", "generated_from", "executed_by", "depends_on"]
    for t in types:
        counts[t] = db.scalar(
            select(func.count(KnowledgeRelation.id)).where(
                KnowledgeRelation.project_id == project_id,
                KnowledgeRelation.relation_type == t,
            )
        ) or 0

    total = sum(counts.values())
    pending = db.scalar(
        select(func.count(KnowledgeRelation.id)).where(
            KnowledgeRelation.project_id == project_id,
            KnowledgeRelation.review_status == "pending",
        )
    ) or 0

    return {
        "total": total,
        "by_type": counts,
        "pending_review": pending,
    }


def _collect_chunk_snapshot(db: Session, project_id: int) -> dict:
    """收集切片维度的快照数据。"""
    total = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.project_id == project_id,
            KnowledgeChunk.status == "active",
        )
    ) or 0

    counts = {}
    chunk_types = ["requirement_rule", "api_schema", "test_case", "defect_case", "execution_result"]
    for t in chunk_types:
        counts[t] = db.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.project_id == project_id,
                KnowledgeChunk.status == "active",
                KnowledgeChunk.chunk_type == t,
            )
        ) or 0

    return {"total": total, "by_type": counts}


def _collect_stats_snapshot(db: Session, project_id: int) -> dict:
    """收集综合统计快照。"""
    source_count = db.scalar(
        select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.status.notin_(("deprecated", "superseded")),
        )
    ) or 0

    return {
        "source_count": source_count,
        "collected_at": datetime.now().isoformat(),
    }


# ── 跨迭代对比 ──

def get_snapshots(db: Session, iteration_id: int) -> list[KnowledgeSnapshot]:
    """获取某个迭代的所有快照。"""
    return list(
        db.scalars(
            select(KnowledgeSnapshot).where(
                KnowledgeSnapshot.iteration_id == iteration_id,
            ).order_by(KnowledgeSnapshot.snapshot_type)
        ).all()
    )


def compare_iterations(
    db: Session,
    base_iteration_id: int,
    target_iteration_id: int,
    project_id: int,
) -> dict | None:
    """对比两个迭代的知识快照。返回 deltas + trends。"""
    base_it = db.get(KnowledgeIteration, base_iteration_id)
    target_it = db.get(KnowledgeIteration, target_iteration_id)
    if not base_it or not target_it or base_it.project_id != project_id or target_it.project_id != project_id:
        return None

    def _get_snapshot_data(it_id: int, snap_type: str) -> dict:
        snap = db.scalar(
            select(KnowledgeSnapshot).where(
                KnowledgeSnapshot.iteration_id == it_id,
                KnowledgeSnapshot.snapshot_type == snap_type,
            )
        )
        if not snap:
            return {}
        try:
            return json.loads(snap.data_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    base_entity = _get_snapshot_data(base_iteration_id, SNAPSHOT_ENTITY)
    target_entity = _get_snapshot_data(target_iteration_id, SNAPSHOT_ENTITY)
    base_relation = _get_snapshot_data(base_iteration_id, SNAPSHOT_RELATION)
    target_relation = _get_snapshot_data(target_iteration_id, SNAPSHOT_RELATION)

    # 计算增量
    entity_delta = (target_entity.get("total", 0) - base_entity.get("total", 0))
    relation_delta = (target_relation.get("total", 0) - base_relation.get("total", 0))

    # 按类型细分
    entity_by_type_delta = {}
    all_types = set(list(base_entity.get("by_type", {}).keys()) + list(target_entity.get("by_type", {}).keys()))
    for t in all_types:
        entity_by_type_delta[t] = target_entity.get("by_type", {}).get(t, 0) - base_entity.get("by_type", {}).get(t, 0)

    relation_by_type_delta = {}
    all_rel_types = set(list(base_relation.get("by_type", {}).keys()) + list(target_relation.get("by_type", {}).keys()))
    for t in all_rel_types:
        relation_by_type_delta[t] = target_relation.get("by_type", {}).get(t, 0) - base_relation.get("by_type", {}).get(t, 0)

    # 趋势指标
    trends = {
        "entity_growth_rate": (entity_delta / base_entity.get("total", 1)) if base_entity.get("total", 0) > 0 else 0,
        "relation_growth_rate": (relation_delta / base_relation.get("total", 1)) if base_relation.get("total", 0) > 0 else 0,
        "avg_confidence_change": round(
            (target_entity.get("avg_confidence", 0) - base_entity.get("avg_confidence", 0)), 4
        ),
        "pending_review_change": (
            target_relation.get("pending_review", 0) - base_relation.get("pending_review", 0)
        ),
    }

    return {
        "base_iteration_id": base_iteration_id,
        "base_iteration_name": base_it.iteration_name,
        "target_iteration_id": target_iteration_id,
        "target_iteration_name": target_it.iteration_name,
        "deltas": {
            "entity_total": entity_delta,
            "relation_total": relation_delta,
            "entity_by_type": entity_by_type_delta,
            "relation_by_type": relation_by_type_delta,
        },
        "trends": {k: round(v, 4) if isinstance(v, float) else v for k, v in trends.items()},
    }


# ── 独立 Session 入口（供 API 在 BackgroundTasks 中调用） ──

def close_iteration_in_new_session(iteration_id: int, project_id: int) -> dict:
    """独立 Session 中关闭迭代并生成快照。"""
    db = SessionLocal()
    try:
        it = close_iteration(db, iteration_id, project_id)
        if not it:
            return {"success": False, "error": "迭代不存在或已关闭"}
        db.commit()
        return {"success": True, "iteration_id": iteration_id, "status": "closed"}
    except Exception:
        logger.exception("Close iteration %s failed", iteration_id)
        db.rollback()
        return {"success": False, "error": "关闭迭代失败"}
    finally:
        db.close()
