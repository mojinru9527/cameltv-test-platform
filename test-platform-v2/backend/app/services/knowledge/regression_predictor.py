"""回归范围预测器（M6）—— 基于 M3 知识图谱分析变更波及面。

核心逻辑：
1. 输入变更的 API paths / modules
2. 查询历史迭代中同一 API 关联的缺陷（affects 关系 + chunk 相似度）
3. 计算缺陷复发概率 → 风险排序
4. 输出预测列表：api_path / risk_score / historical_defects / suggested_test_cases
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func, select, text

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeChunk, KnowledgeEntity, KnowledgeRelation

logger = logging.getLogger("knowledge.regression")


def predict_regression_scope(
    project_id: int,
    changed_paths: list[str] | None = None,
    changed_modules: list[str] | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    """预测变更波及的回归范围。

    Args:
        project_id: 项目 ID
        changed_paths: 变更的 API paths（如 ["GET:/users", "POST:/orders"]）
        changed_modules: 变更的模块名
        top_k: 返回 top-K 结果

    Returns:
        {"items": [...], "total_analyzed": N, "high_risk_count": N}
    """
    changed_paths = changed_paths or []
    changed_modules = changed_modules or []

    db = SessionLocal()
    items: list[dict] = []

    try:
        # 1. 收集所有受影响的 API 实体
        affected_paths = list(changed_paths)

        if changed_modules:
            # 按模块模糊匹配 entity_key 中有 module 信息的 API
            for module in changed_modules:
                module_entities = list(
                    db.scalars(
                        select(KnowledgeEntity).where(
                            KnowledgeEntity.project_id == project_id,
                            KnowledgeEntity.entity_type == "api",
                            KnowledgeEntity.entity_key.contains(module),
                        )
                    ).all()
                )
                for e in module_entities:
                    affected_paths.append(e.name)

        # 去重
        affected_paths = list(set(affected_paths))

        if not affected_paths:
            # 无变更，返回空
            return {"items": [], "total_analyzed": 0, "high_risk_count": 0}

        # 2. 对每个变更的 API，计算风险分数
        for path in affected_paths:
            risk = _calculate_risk_for_path(db, project_id, path)
            items.append(risk)

        # 3. 按 risk_score 降序排列
        items.sort(key=lambda x: x["risk_score"], reverse=True)

        # 4. 截断
        result_items = items[:top_k]
        high_risk = sum(1 for i in result_items if i["risk_score"] >= 0.5)

        return {
            "items": result_items,
            "total_analyzed": len(items),
            "high_risk_count": high_risk,
        }

    except Exception:
        logger.exception("Regression prediction failed for project %s", project_id)
        return {"items": [], "total_analyzed": 0, "high_risk_count": 0}
    finally:
        db.close()


def _calculate_risk_for_path(db, project_id: int, api_path: str) -> dict:
    """计算单个 API path 的回归风险分数。"""
    # 2a. 查找该 API 的实体
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_type == "api",
            KnowledgeEntity.name == api_path,
        )
    )

    # 2b. 查询历史关联的缺陷（affects 关系：defect → api）
    historical_defects: list[str] = []
    defect_count = 0

    if entity:
        # 查找指向该实体的 affects 关系
        relations = list(
            db.scalars(
                select(KnowledgeRelation).where(
                    KnowledgeRelation.project_id == project_id,
                    KnowledgeRelation.to_entity_id == entity.id,
                    KnowledgeRelation.relation_type == "affects",
                )
            ).all()
        )

        defect_entity_ids = [r.from_entity_id for r in relations]
        if defect_entity_ids:
            defect_entities = list(
                db.scalars(
                    select(KnowledgeEntity).where(
                        KnowledgeEntity.id.in_(defect_entity_ids),
                        KnowledgeEntity.entity_type == "defect",
                    )
                ).all()
            )
            historical_defects = [e.name[:120] for e in defect_entities]
            defect_count = len(defect_entities)

    # 2c. 搜索相关 test_case（通过 generated_from 或 covers 关系）
    suggested_test_cases: list[str] = []
    if entity:
        test_relations = list(
            db.scalars(
                select(KnowledgeRelation).where(
                    KnowledgeRelation.project_id == project_id,
                    KnowledgeRelation.to_entity_id == entity.id,
                    KnowledgeRelation.relation_type.in_(("generated_from", "covers")),
                )
            ).all()
        )
        test_entity_ids = [r.from_entity_id for r in test_relations]
        if test_entity_ids:
            test_entities = list(
                db.scalars(
                    select(KnowledgeEntity).where(
                        KnowledgeEntity.id.in_(test_entity_ids),
                        KnowledgeEntity.entity_type == "test_case",
                    )
                ).all()
            )
            suggested_test_cases = [e.name[:120] for e in test_entities]

    # 2d. 搜索相关 chunks（关键词检索）
    related_chunks_count = 0
    try:
        related_chunks_count = db.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.project_id == project_id,
                KnowledgeChunk.status == "active",
                KnowledgeChunk.content.contains(api_path.split(":")[-1] if ":" in api_path else api_path),
            )
        ) or 0
    except Exception:
        pass

    # 2e. 计算风险分数（0-1）
    # 公式：缺陷频率 + 关联密度因子
    defect_score = min(defect_count / 5.0, 0.6)  # 最多 0.6
    chunk_score = min(related_chunks_count / 20.0, 0.2)  # 最多 0.2
    test_score = min(len(suggested_test_cases) / 10.0, 0.2)  # 最多 0.2
    risk_score = round(defect_score + chunk_score + test_score, 2)

    # 提取 module（从 entity_key 中）
    module = ""
    if entity and entity.entity_key:
        parts = entity.entity_key.split(":")
        if len(parts) >= 2:
            module = parts[1]

    return {
        "api_path": api_path,
        "module": module,
        "risk_score": min(risk_score, 1.0),
        "historical_defects": defect_count,
        "suggested_test_cases": suggested_test_cases[:5],
        "affected_entities": historical_defects[:3],
    }
