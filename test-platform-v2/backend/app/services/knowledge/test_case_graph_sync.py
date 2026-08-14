# -*- coding: utf-8 -*-
"""Batch 132 — 全量用例入图 + 来源回填（C125-3 / C126-1）。

将项目全部 active 用例落为 knowledge_entity（entity_type=test_case），
统一挂到"用例库全量"知识源（knowledge_domain=project），消除用例实体来源待补；
复用 test_case_linker 策略为能关联模块的用例建立 tested_by 关联（幂等）。

幂等：按 entity_key（test_case:p{pid}:{case.id}）upsert，重复执行不产生重复实体。
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeEntity, KnowledgeSource
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.services.knowledge.test_case_linker import (
    _test_case_entity_key,
    link_test_cases_to_module,
)

logger = logging.getLogger("knowledge.test_case_graph_sync")

LIBRARY_SOURCE_TITLE = "用例库全量"
LIBRARY_SOURCE_REF = "test-case-library"


def ensure_case_library_source(db: Session, project_id: int) -> KnowledgeSource:
    """Get or create the per-project '用例库全量' knowledge source (project domain)."""
    src = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.project_id == project_id,
            KnowledgeSource.source_type == "test_case",
            KnowledgeSource.title == LIBRARY_SOURCE_TITLE,
        )
    )
    if src:
        return src
    src = KnowledgeSource(
        project_id=project_id,
        source_type="test_case",
        title=LIBRARY_SOURCE_TITLE,
        source_ref=LIBRARY_SOURCE_REF,
        knowledge_domain="project",
        para_category="resource",
        status="active",
        freshness_score=1.0,
    )
    db.add(src)
    db.flush()
    return src


def sync_all_test_cases_to_graph(db: Session, project_id: int) -> dict:
    """全量用例入图：upsert 用例实体 + 回填来源 + 关联模块，返回统计。"""
    library = ensure_case_library_source(db, project_id)
    cases = list(
        db.scalars(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
            )
        ).all()
    )

    created = source_backfilled = 0
    for case in cases:
        key = _test_case_entity_key(project_id, case.id)
        ent = db.scalar(
            select(KnowledgeEntity).where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_key == key,
            )
        )
        if ent is None:
            ent = KnowledgeEntity(
                project_id=project_id,
                entity_type="test_case",
                entity_key=key,
                name=case.title or f"用例 {case.case_id}",
                description=f"test_case: {case.title or case.case_id}",
                confidence=1.0,
                review_status="approved",
                source_id=library.id,
                business_ref_type="test_case",
                business_ref_id=case.id,
            )
            db.add(ent)
            created += 1
        else:
            # C126-1 来源回填：存量用例实体补 source_id
            if ent.source_id is None or ent.source_id != library.id:
                ent.source_id = library.id
                source_backfilled += 1
            if not ent.business_ref_id:
                ent.business_ref_id = case.id
            if not ent.name:
                ent.name = case.title or f"用例 {case.case_id}"
    db.flush()

    # 关联模块：能关联的用例建立 tested_by（复用 linker 策略，幂等）
    linked_cases = 0
    modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == project_id,
                RequirementModule.node_type.in_(["module", "page"]),
            )
        ).all()
    )
    for module in modules:
        result = link_test_cases_to_module(
            db,
            module=module,
            test_cases=cases,
            project_id=project_id,
            version="",
        )
        linked_cases += result.linked_count

    db.commit()

    total_entities = (
        db.scalar(
            select(func.count())
            .select_from(KnowledgeEntity)
            .where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_type == "test_case",
            )
        )
        or 0
    )
    logger.info(
        "sync_all_test_cases_to_graph: project=%d cases=%d entities=%d created=%d backfilled=%d linked=%d",
        project_id, len(cases), total_entities, created, source_backfilled, linked_cases,
    )
    return {
        "total_cases": len(cases),
        "test_case_entities": total_entities,
        "created": created,
        "source_backfilled": source_backfilled,
        "linked_cases": linked_cases,
    }
