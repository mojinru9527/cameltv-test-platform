"""知识图谱实体提取服务（M3）

从 knowledge_chunk 中提取结构化实体（API/参数/错误码/需求/缺陷/用例）并写入 knowledge_entity。
提取策略：规则驱动（正则 + 字段解析），不依赖外部 LLM（速度、成本、确定性）。
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeChunk, KnowledgeEntity, KnowledgeRelation, KnowledgeSource

logger = logging.getLogger("knowledge.entity")

# ── 提取正则 ──
_API_RE = re.compile(
    r"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S+)", re.IGNORECASE,
)
_FIELD_RE = re.compile(r'"(\w+)"\s*:\s*[{[]')  # JSON field names from schema content
_ERROR_CODE_RE = re.compile(r'("errorCode"\s*:\s*"?(\w+)"?|code[:\s]+(\d{3,6}))')
_REQ_TITLE_RE = re.compile(r"需求[：:]\s*(.+)")
_DOMAIN_RE = re.compile(r"module[：:]\s*(\w+)", re.IGNORECASE)


def _entity_key(entity_type: str, project_id: int, name: str) -> str:
    """生成稳定的实体唯一键。"""
    return f"{entity_type}:p{project_id}:{name}"


def _entity_exists(db, project_id: int, entity_key: str) -> bool:
    return db.scalar(
        select(KnowledgeEntity.id).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == entity_key,
        )
    ) is not None


def extract_api_entities(
    chunk: KnowledgeChunk, source: KnowledgeSource | None
) -> list[dict[str, Any]]:
    """从 api_schema 切片提取 API 级实体和字段级实体。"""
    entities: list[dict[str, Any]] = []
    content = chunk.content or ""

    # API 级实体：匹配 HTTP method + path
    matches = _API_RE.findall(content)
    for method, path in matches:
        method = method.upper()
        name = f"{method} {path}"
        entity_key = _entity_key("api", chunk.project_id, name)
        entities.append({
            "entity_type": "api",
            "entity_key": entity_key,
            "name": name,
            "description": source.title if source else f"API 端点 {name}",
            "source_id": chunk.source_id,
            "confidence": 0.9,
            "metadata_json": json.dumps({"method": method, "path": path}, ensure_ascii=False),
        })

    # 字段级实体：从 JSON schema 提取字段名
    field_matches = set(_FIELD_RE.findall(content))
    service_name = (source.title if source else "").replace("接口导入 ", "").split(" 批次")[0]
    for field_name in list(field_matches)[:20]:  # 限制字段数量
        entity_key = _entity_key("field", chunk.project_id, f"{service_name}:{field_name}")
        entities.append({
            "entity_type": "field",
            "entity_key": entity_key,
            "name": field_name,
            "description": f"参数 {field_name}（来自 {service_name}）",
            "source_id": chunk.source_id,
            "confidence": 0.7,
            "metadata_json": json.dumps({"service": service_name}, ensure_ascii=False),
        })

    # 错误码实体
    error_matches = set()
    for m in _ERROR_CODE_RE.finditer(content):
        code = m.group(2) or m.group(3)
        if code:
            error_matches.add(code)
    for code in list(error_matches)[:10]:
        entity_key = _entity_key("field", chunk.project_id, f"error:{code}")
        entities.append({
            "entity_type": "field",
            "entity_key": entity_key,
            "name": f"错误码 {code}",
            "description": f"API 错误码 {code}",
            "source_id": chunk.source_id,
            "confidence": 0.6,
            "metadata_json": json.dumps({"error_code": code}, ensure_ascii=False),
        })

    return entities


def extract_requirement_entities(
    chunk: KnowledgeChunk, source: KnowledgeSource | None
) -> list[dict[str, Any]]:
    """从 requirement_rule 切片提取需求/业务规则实体。"""
    content = chunk.content or ""
    entities: list[dict[str, Any]] = []
    source_title = source.title if source else f"需求文档 #{chunk.source_id}"

    # 提取标题中的需求名称
    title_match = _REQ_TITLE_RE.search(content)
    if title_match:
        name = title_match.group(1).strip()[:80]
    else:
        name = source_title[:80]

    entity_key = _entity_key("requirement", chunk.project_id, name)
    entities.append({
        "entity_type": "requirement",
        "entity_key": entity_key,
        "name": name,
        "description": source_title,
        "source_id": chunk.source_id,
        "business_ref_type": "requirement",
        "business_ref_id": source.source_id if source else None,
        "confidence": 0.85,
        "metadata_json": json.dumps({"source_type": "requirement"}, ensure_ascii=False),
    })

    return entities


def extract_test_case_entities(
    chunk: KnowledgeChunk, source: KnowledgeSource | None
) -> list[dict[str, Any]]:
    """从 test_case 切片提取用例实体。"""
    content = chunk.content or ""
    entities: list[dict[str, Any]] = []

    # 解析标题和 API 端点
    lines = content.split("\n")
    title = lines[0] if lines else (source.title if source else f"用例 #{chunk.source_id}")

    entity_key = _entity_key("test_case", chunk.project_id, title[:80])
    entities.append({
        "entity_type": "test_case",
        "entity_key": entity_key,
        "name": title[:80],
        "description": f"接口用例：{title[:80]}",
        "source_id": chunk.source_id,
        "business_ref_type": "test_case",
        "business_ref_id": source.source_id if source else None,
        "confidence": 0.85,
        "metadata_json": json.dumps({"source_type": "test_case"}, ensure_ascii=False),
    })

    return entities


def extract_defect_entities(
    chunk: KnowledgeChunk, source: KnowledgeSource | None
) -> list[dict[str, Any]]:
    """从 defect_case 切片提取缺陷实体。"""
    content = chunk.content or ""
    entities: list[dict[str, Any]] = []

    lines = content.split("\n")
    title = lines[0] if lines else "Unknown defect"
    severity = "medium"
    for line in lines[:3]:
        if line.startswith("[") and "]" in line:
            severity = line[1:line.index("]")]

    entity_key = _entity_key("defect", chunk.project_id, title[:80])
    entities.append({
        "entity_type": "defect",
        "entity_key": entity_key,
        "name": title[:80],
        "description": f"缺陷（{severity}）：{title[:80]}",
        "source_id": chunk.source_id,
        "business_ref_type": "defect",
        "business_ref_id": source.source_id if source else None,
        "confidence": 0.85,
        "metadata_json": json.dumps({"severity": severity}, ensure_ascii=False),
    })

    return entities


# ── 提取调度 ──

_EXTRACTORS = {
    "api_schema": extract_api_entities,
    "requirement_rule": extract_requirement_entities,
    "test_case": extract_test_case_entities,
    "defect_case": extract_defect_entities,
}


def extract_entities_from_chunk(
    chunk: KnowledgeChunk, source: KnowledgeSource | None
) -> list[dict[str, Any]]:
    """按 chunk_type 分派提取器。"""
    extractor = _EXTRACTORS.get(chunk.chunk_type)
    if not extractor:
        return []
    try:
        return extractor(chunk, source)
    except Exception:
        logger.exception("Entity extraction failed for chunk %s (type=%s)", chunk.id, chunk.chunk_type)
        return []


# ── 关系构建 ──

def _rel_exists(db, project_id: int, from_id: int, to_id: int, rel_type: str) -> bool:
    """检查关系是否已存在（去重）。"""
    return db.scalar(
        select(KnowledgeRelation.id).where(
            KnowledgeRelation.project_id == project_id,
            KnowledgeRelation.from_entity_id == from_id,
            KnowledgeRelation.to_entity_id == to_id,
            KnowledgeRelation.relation_type == rel_type,
        )
    ) is not None


def _build_relations(
    db,
    project_id: int,
    new_entities: list[KnowledgeEntity],
    all_entities: list[KnowledgeEntity],
) -> list[dict[str, Any]]:
    """从提取的实体列表中构建关系（contains / executed_by / affects / covers / generated_from）。"""
    relations: list[dict[str, Any]] = []
    # 索引已存在实体
    by_key: dict[str, KnowledgeEntity] = {e.entity_key: e for e in all_entities}
    # 索引：name → entity 列表（用于模糊匹配）
    by_name: dict[str, list[KnowledgeEntity]] = defaultdict(list)
    for e in all_entities:
        by_name[e.name.lower()].append(e)

    # ── 1. contains: API → field（同一 source 内） ──
    by_source: dict[int, list[KnowledgeEntity]] = defaultdict(list)
    for e in new_entities:
        if e.source_id:
            by_source[e.source_id].append(e)

    for sid, group in by_source.items():
        if len(group) < 2:
            continue
        apis = [e for e in group if e.entity_type == "api"]
        fields = [e for e in group if e.entity_type == "field"]
        for api_e in apis:
            for field_e in fields:
                if not _rel_exists(db, project_id, api_e.id, field_e.id, "contains"):
                    relations.append({
                        "from_entity_id": api_e.id,
                        "relation_type": "contains",
                        "to_entity_id": field_e.id,
                        "confidence": 0.7,
                        "evidence_chunk_ids": json.dumps([sid]),
                    })

    # ── 2. executed_by: test_case → 同源实体（共现/业务引用） ──
    for e in new_entities:
        if e.entity_type == "test_case" and e.business_ref_id:
            ref_id = e.business_ref_id
            same_source = db.scalars(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.business_ref_id == ref_id,
                    KnowledgeEntity.entity_type != "test_case",
                )
            ).all()
            for other in same_source:
                if not _rel_exists(db, project_id, e.id, other.id, "executed_by"):
                    relations.append({
                        "from_entity_id": e.id,
                        "relation_type": "executed_by",
                        "to_entity_id": other.id,
                        "confidence": 0.6,
                    })

    # ── 3. affects: defect → API（缺陷影响范围） ──
    for e in new_entities:
        if e.entity_type != "defect":
            continue
        source = db.get(KnowledgeSource, e.source_id) if e.source_id else None
        # 从 source 关联的 chunk content 中提取受影响 API
        if source:
            related_chunks = db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.source_id == e.source_id)
            ).all()
            for chunk in related_chunks:
                api_matches = _API_RE.findall(chunk.content or "")
                for method, path in api_matches:
                    api_name = f"{method.upper()} {path}"
                    api_key = _entity_key("api", project_id, api_name)
                    api_entity = by_key.get(api_key)
                    if api_entity and not _rel_exists(db, project_id, e.id, api_entity.id, "affects"):
                        relations.append({
                            "from_entity_id": e.id,
                            "relation_type": "affects",
                            "to_entity_id": api_entity.id,
                            "confidence": 0.55,
                            "evidence_chunk_ids": json.dumps([chunk.id]),
                        })
                        break  # 每个缺陷只关联第一个匹配 API

    # ── 4. covers: test_case → requirement（用例覆盖需求） ──
    for e in new_entities:
        if e.entity_type != "test_case":
            continue
        # 查找同 project 下的 requirement 实体
        req_entities = [ent for ent in all_entities if ent.entity_type == "requirement" and ent.project_id == project_id]
        source = db.get(KnowledgeSource, e.source_id) if e.source_id else None
        if source and source.source_ref:
            # source_ref 中可能包含需求引用
            for req_e in req_entities:
                if req_e.name in (source.source_ref or ""):
                    if not _rel_exists(db, project_id, e.id, req_e.id, "covers"):
                        relations.append({
                            "from_entity_id": e.id,
                            "relation_type": "covers",
                            "to_entity_id": req_e.id,
                            "confidence": 0.5,
                        })
                    break

    # ── 5. generated_from: test_case → API（AI 从接口生成用例） ──
    for e in new_entities:
        if e.entity_type != "test_case":
            continue
        source = db.get(KnowledgeSource, e.source_id) if e.source_id else None
        if not source or not source.source_ref:
            continue
        # source_ref 如 "GET /api/v1/users" → 查找匹配的 API 实体
        api_match = _API_RE.search(source.source_ref)
        if api_match:
            method, path = api_match.group(1).upper(), api_match.group(2)
            api_name = f"{method} {path}"
            api_key = _entity_key("api", project_id, api_name)
            api_entity = by_key.get(api_key)
            if api_entity and not _rel_exists(db, project_id, e.id, api_entity.id, "generated_from"):
                relations.append({
                    "from_entity_id": e.id,
                    "relation_type": "generated_from",
                    "to_entity_id": api_entity.id,
                    "confidence": 0.65,
                })

    return relations


# ── 入口：批量提取 ──

def extract_and_build_graph_in_new_session(
    project_id: int,
    source_id: int | None = None,
    max_chunks: int = 100,
) -> dict[str, int]:
    """独立 Session 批量提取实体+关系。"""
    from app.core.config import settings

    if not settings.knowledge_graph_enabled:
        return {"extracted": 0, "relations": 0, "skipped": 0, "message": "知识图谱未启用"}

    db = SessionLocal()
    extracted = 0
    relations_count = 0
    skipped = 0
    try:
        # 查询待处理切片
        stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.project_id == project_id,
            KnowledgeChunk.is_deleted.is_(False),
        )
        if source_id:
            stmt = stmt.where(KnowledgeChunk.source_id == source_id)
        chunks = list(db.scalars(stmt.limit(max_chunks)).all())

        # 加载所有已存在实体 key（避免重复）
        existing_keys = set(
            db.scalars(
                select(KnowledgeEntity.entity_key).where(
                    KnowledgeEntity.project_id == project_id,
                )
            ).all()
        )

        new_entity_objs: list[KnowledgeEntity] = []
        for chunk in chunks:
            source = db.get(KnowledgeSource, chunk.source_id) if chunk.source_id else None
            raw_entities = extract_entities_from_chunk(chunk, source)
            for raw in raw_entities:
                if raw["entity_key"] in existing_keys:
                    skipped += 1
                    continue
                entity = KnowledgeEntity(
                    project_id=project_id,
                    entity_type=raw["entity_type"],
                    entity_key=raw["entity_key"],
                    name=raw["name"],
                    description=raw.get("description", ""),
                    source_id=raw.get("source_id"),
                    business_ref_type=raw.get("business_ref_type", ""),
                    business_ref_id=raw.get("business_ref_id"),
                    confidence=raw.get("confidence", 0.0),
                    metadata_json=raw.get("metadata_json", "{}"),
                )
                db.add(entity)
                new_entity_objs.append(entity)
                existing_keys.add(raw["entity_key"])
                extracted += 1

        if new_entity_objs:
            db.flush()  # 获取 auto-increment IDs

            # 加载所有实体（新+旧）用于关系构建
            all_entities = list(
                db.scalars(
                    select(KnowledgeEntity).where(KnowledgeEntity.project_id == project_id)
                ).all()
            )
            rel_raws = _build_relations(db, project_id, new_entity_objs, all_entities)
            for rel in rel_raws:
                relation = KnowledgeRelation(
                    project_id=project_id,
                    from_entity_id=rel["from_entity_id"],
                    relation_type=rel["relation_type"],
                    to_entity_id=rel["to_entity_id"],
                    confidence=rel.get("confidence", 0.0),
                    evidence_chunk_ids=rel.get("evidence_chunk_ids", "[]"),
                )
                db.add(relation)
                relations_count += 1

        db.commit()
        logger.info(
            "Graph build done project=%s: extracted=%s relations=%s skipped=%s",
            project_id, extracted, relations_count, skipped,
        )
    except Exception:
        logger.exception("Graph build failed for project %s", project_id)
        db.rollback()
    finally:
        db.close()

    return {
        "extracted": extracted,
        "relations": relations_count,
        "skipped": skipped,
        "message": f"提取 {extracted} 实体 + {relations_count} 关系，{skipped} 重复跳过",
    }


# ── 概念地图自演化 ──

def backfill_missing_source(db, project_id: int) -> dict:
    """C147-9: 回填缺失 source_id 的实体（按名称匹配用例/需求）。"""
    from app.models.requirement import RequirementDocument
    from app.models.test_case import TestCase

    rows = db.scalars(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.source_id.is_(None),
        )
    ).all()
    updated = 0
    unmatched = 0
    for ent in rows:
        name = (ent.name or "").strip()
        if not name:
            unmatched += 1
            continue
        # 用例匹配：case_id 编码（TC-xxx）或标题
        case = db.scalar(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                (TestCase.case_id == name) | (TestCase.title == name),
            ).limit(1)
        )
        if case:
            ent.source_id = case.id
            ent.source_ref = f"test_case:{case.id}"
            updated += 1
            continue
        # 需求匹配：标题
        doc = db.scalar(
            select(RequirementDocument).where(
                RequirementDocument.project_id == project_id,
                RequirementDocument.title == name,
            ).limit(1)
        )
        if doc:
            ent.source_id = doc.id
            ent.source_ref = f"requirement:{doc.id}"
            updated += 1
            continue
        unmatched += 1
    db.commit()
    return {"total": len(rows), "updated": updated, "unmatched": unmatched}


def evolve_graph_in_new_session(project_id: int, db: Session | None = None) -> dict:
    """概念地图自演化：合并重复实体 + 更新置信度 + 发现隐含关系。

    独立 Session，供定时任务或手动触发调用。
    返回演化统计信息。
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    merged = 0
    confidence_updates = 0
    new_relations = 0
    try:
        # ── 1. 合并重复实体（同类型 + 同名称） ──
        all_entities = list(
            db.scalars(
                select(KnowledgeEntity)
                .where(KnowledgeEntity.project_id == project_id)
                .order_by(KnowledgeEntity.id)
            ).all()
        )

        # 按 (entity_type, name) 分组，找出重复
        groups: dict[tuple[str, str], list[KnowledgeEntity]] = defaultdict(list)
        for e in all_entities:
            key = (e.entity_type, e.name.strip().lower())
            groups[key].append(e)

        for (etype, name), group in groups.items():
            if len(group) <= 1:
                continue
            # 保留最早创建的实体为主实体，合并其余
            master = group[0]
            for dup in group[1:]:
                # 将重复实体的关系重定向到主实体
                rels = list(
                    db.scalars(
                        select(KnowledgeRelation).where(
                            KnowledgeRelation.project_id == project_id,
                            (KnowledgeRelation.from_entity_id == dup.id)
                            | (KnowledgeRelation.to_entity_id == dup.id),
                        )
                    ).all()
                )
                for rel in rels:
                    if rel.from_entity_id == dup.id:
                        rel.from_entity_id = master.id
                    if rel.to_entity_id == dup.id:
                        rel.to_entity_id = master.id
                    rel.metadata_json = json.dumps({
                        **json.loads(rel.metadata_json or "{}"),
                        "merged_from": dup.id,
                    })

                # 提高主实体置信度
                master.confidence = min(1.0, master.confidence + dup.confidence * 0.3)
                # 标记重复实体为已合并
                dup.description = f"[已合并至 #{master.id}] {dup.description}"
                dup.confidence = 0.0
                merged += 1

        if merged > 0:
            db.flush()

        # ── 2. 基于关系数量更新置信度 ──
        from sqlalchemy import func as sa_func

        for entity in all_entities:
            if entity.confidence <= 0:
                continue
            rel_count = db.scalar(
                select(sa_func.count(KnowledgeRelation.id)).where(
                    KnowledgeRelation.project_id == project_id,
                    (KnowledgeRelation.from_entity_id == entity.id)
                    | (KnowledgeRelation.to_entity_id == entity.id),
                )
            ) or 0
            # 关系越多置信度越高（但上限为已有置信度与基于关系数的置信度的加权平均）
            rel_confidence = min(1.0, rel_count * 0.15)
            new_conf = round(entity.confidence * 0.7 + rel_confidence * 0.3, 3)
            if abs(new_conf - entity.confidence) > 0.01:
                entity.confidence = new_conf
                confidence_updates += 1

        if confidence_updates > 0:
            db.flush()

        # ── 3. 发现隐含关系：共享相同 chunk 来源的实体间建立 related_to 关系 ──
        # 找出所有 source_id（关联到 knowledge_source 的实体）
        entity_source_map: dict[int, list[KnowledgeEntity]] = defaultdict(list)
        for e in all_entities:
            if e.source_id:
                entity_source_map[e.source_id].append(e)

        existing_relation_pairs: set[tuple[int, int, str]] = set()
        for rel in db.scalars(
            select(KnowledgeRelation).where(KnowledgeRelation.project_id == project_id)
        ).all():
            existing_relation_pairs.add((rel.from_entity_id, rel.to_entity_id, rel.relation_type))

        for source_id, entities in entity_source_map.items():
            if len(entities) < 2:
                continue
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    a, b = entities[i], entities[j]
                    if a.confidence <= 0 or b.confidence <= 0:
                        continue
                    # 跳过已有关系
                    if (a.id, b.id, "related_to") in existing_relation_pairs:
                        continue
                    if (b.id, a.id, "related_to") in existing_relation_pairs:
                        continue
                    rel = KnowledgeRelation(
                        project_id=project_id,
                        from_entity_id=a.id,
                        relation_type="related_to",
                        to_entity_id=b.id,
                        confidence=round(min(a.confidence, b.confidence) * 0.6, 3),
                        evidence_chunk_ids=json.dumps([source_id]),
                    )
                    db.add(rel)
                    existing_relation_pairs.add((a.id, b.id, "related_to"))
                    new_relations += 1

        db.commit()

        # ── 4. 记录演化事件为知识源 ──
        if merged > 0 or new_relations > 0:
            try:
                from app.services.knowledge.source_service import record_source
                event_content = json.dumps({
                    "merged_entities": merged,
                    "confidence_updates": confidence_updates,
                    "new_relations": new_relations,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False)
                record_source(
                    db,
                    project_id=project_id,
                    source_type="graph_evolution",
                    source_id=None,
                    title=f"图谱自演化 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    source_ref="",
                    raw_content=event_content,
                    metadata={
                        "merged": merged,
                        "confidence_updates": confidence_updates,
                        "new_relations": new_relations,
                    },
                )
                db.commit()
            except Exception:
                logger.exception("Failed to record evolution event")

        summary = {
            "merged": merged,
            "confidence_updates": confidence_updates,
            "new_relations": new_relations,
            "message": f"合并 {merged} 重复实体, 更新 {confidence_updates} 置信度, 发现 {new_relations} 隐含关系",
        }
        logger.info("Graph evolution project=%s: %s", project_id, summary["message"])
        return summary

    except Exception as e:
        logger.exception("Graph evolution failed for project %s", project_id)
        db.rollback()
        return {"merged": 0, "confidence_updates": 0, "new_relations": 0, "error": str(e)}
    finally:
        if own_session:
            db.close()


# ── 图谱查询/写入（Batch 181 P2-10：路由层 ORM 收敛） ──

def knowledge_domain_filter(pid: int, knowledge_domain: str | None):
    """知识域过滤（Batch 132 分域隔离）。

    platform 仅展示来源=platform 的实体；project 展示来源=project 与无来源孤儿实体
    （孤儿默认归属项目域）；None 不限制。两域不再共用同一批孤儿数据。
    """
    if not knowledge_domain:
        return None
    source_ids = select(KnowledgeSource.id).where(
        KnowledgeSource.project_id == pid,
        KnowledgeSource.knowledge_domain == knowledge_domain,
    )
    if knowledge_domain == "platform":
        return KnowledgeEntity.source_id.in_(source_ids)
    return KnowledgeEntity.source_id.in_(source_ids) | KnowledgeEntity.source_id.is_(None)


def get_entity_stats(
    db: Session,
    project_id: int,
    *,
    entity_type: str | None = None,
    keyword: str | None = None,
    knowledge_domain: str | None = None,
) -> dict:
    """实体统计（project-wide 全量，与列表 limit 无关）。"""
    from app.models.test_case import TestCase

    pid = project_id
    filters = [KnowledgeEntity.project_id == pid]
    domain_cond = knowledge_domain_filter(pid, knowledge_domain)
    if domain_cond is not None:
        filters.append(domain_cond)
    if entity_type:
        filters.append(KnowledgeEntity.entity_type == entity_type)
    if keyword:
        filters.append(
            KnowledgeEntity.name.contains(keyword)
            | KnowledgeEntity.description.contains(keyword)
        )

    rows = db.execute(
        select(KnowledgeEntity.entity_type, func.count(KnowledgeEntity.id))
        .where(*filters)
        .group_by(KnowledgeEntity.entity_type)
    ).all()
    by_type = {kind: count for kind, count in rows}
    missing_source = db.scalar(
        select(func.count(KnowledgeEntity.id)).where(
            *filters,
            KnowledgeEntity.source_id.is_(None),
        )
    ) or 0
    # Batch 132: 用例库全量（权威口径），用于"已入库/全量"展示
    test_case_total = db.scalar(
        select(func.count(TestCase.id)).where(
            TestCase.project_id == pid,
            TestCase.is_deleted.is_(False),
        )
    ) or 0
    return {
        "total": sum(by_type.values()),
        "by_type": by_type,
        "missing_source": missing_source,
        "test_case_total": test_case_total,
    }


def get_entities(
    db: Session,
    project_id: int,
    *,
    entity_type: str | None = None,
    keyword: str | None = None,
    knowledge_domain: str | None = None,
    limit: int = 200,
) -> tuple[list[KnowledgeEntity], dict[int, tuple[str, str]]]:
    """实体列表 + 来源映射（source_id → (title, source_type)），供路由组装精简视图。"""
    pid = project_id
    stmt = select(KnowledgeEntity).where(KnowledgeEntity.project_id == pid)
    domain_cond = knowledge_domain_filter(pid, knowledge_domain)
    if domain_cond is not None:
        stmt = stmt.where(domain_cond)
    if entity_type:
        stmt = stmt.where(KnowledgeEntity.entity_type == entity_type)
    if keyword:
        stmt = stmt.where(KnowledgeEntity.name.contains(keyword) | KnowledgeEntity.description.contains(keyword))
    rows = db.scalars(stmt.order_by(KnowledgeEntity.id.desc()).limit(limit)).all()
    source_ids = {r.source_id for r in rows if r.source_id}
    source_map: dict[int, tuple[str, str]] = {}
    if source_ids:
        src_rows = db.execute(
            select(KnowledgeSource.id, KnowledgeSource.title, KnowledgeSource.source_type).where(
                KnowledgeSource.id.in_(source_ids)
            )
        ).all()
        source_map = {sid: (title or "", stype or "") for sid, title, stype in src_rows}
    return list(rows), source_map


def get_entity_with_source(
    db: Session, entity_pk: int, project_id: int,
) -> tuple[KnowledgeEntity | None, KnowledgeSource | None]:
    """实体详情 + 关联知识源对象（路由不再直连 ORM）。"""
    entity = db.get(KnowledgeEntity, entity_pk)
    if not entity or entity.project_id != project_id:
        return None, None
    src = db.get(KnowledgeSource, entity.source_id) if entity.source_id else None
    return entity, src


def get_relations(
    db: Session,
    project_id: int,
    *,
    entity_id: int | None = None,
    relation_type: str | None = None,
    limit: int = 200,
) -> list[KnowledgeRelation]:
    """项目内知识图谱关系列表。"""
    pid = project_id
    stmt = select(KnowledgeRelation).where(KnowledgeRelation.project_id == pid)
    if entity_id:
        stmt = stmt.where(KnowledgeRelation.from_entity_id == entity_id)
    if relation_type:
        stmt = stmt.where(KnowledgeRelation.relation_type == relation_type)
    return list(db.scalars(stmt.order_by(KnowledgeRelation.id.desc()).limit(limit)).all())


def get_graph_view_data(
    db: Session,
    project_id: int,
    *,
    knowledge_domain: str | None = None,
    limit: int = 200,
) -> tuple[list[KnowledgeEntity], list[KnowledgeRelation]]:
    """图谱可视化数据源（entities + relations，支持知识域过滤）。"""
    pid = project_id
    stmt = select(KnowledgeEntity).where(KnowledgeEntity.project_id == pid)
    if knowledge_domain:
        # Batch 132 分域隔离：platform 仅来源=platform；project 含来源=project 与
        # 无来源孤儿实体（孤儿默认归属项目域）。两域不再共用同一批数据。
        domain_cond = knowledge_domain_filter(pid, knowledge_domain)
        if domain_cond is not None:
            stmt = stmt.where(domain_cond)
    entities = list(db.scalars(stmt.limit(limit)).all())
    relations = list(
        db.scalars(
            select(KnowledgeRelation).where(KnowledgeRelation.project_id == pid).limit(limit)
        ).all()
    )
    return entities, relations


def review_relation(
    db: Session,
    relation_pk: int,
    project_id: int,
    review_status: str,
    comment: str,
) -> KnowledgeRelation | None:
    """采纳/驳回关系：写 review_status 并把 comment 并入 metadata_json。"""
    rel = db.get(KnowledgeRelation, relation_pk)
    if not rel or rel.project_id != project_id:
        return None
    rel.review_status = review_status
    rel.metadata_json = json.dumps({**json.loads(rel.metadata_json or "{}"), "comment": comment})
    db.flush()
    return rel


def import_module_associations(
    db: Session,
    project_id: int,
    entities: list,
    relations: list,
) -> dict:
    """体育模块关联入库（Batch 122 用例结构），幂等。返回入库计数。"""
    pid = project_id
    created_e = created_r = skipped_e = skipped_r = 0
    key_to_id: dict[str, int] = {}

    def _ensure_entity(ent) -> int:
        nonlocal created_e, skipped_e
        eid = key_to_id.get(ent.entity_key)
        if eid:
            return eid
        row = db.scalar(select(KnowledgeEntity.id).where(
            KnowledgeEntity.project_id == pid,
            KnowledgeEntity.entity_key == ent.entity_key,
        ))
        if row:
            skipped_e += 1
            key_to_id[ent.entity_key] = row
            return row
        row = KnowledgeEntity(
            project_id=pid,
            entity_type=ent.entity_type,
            entity_key=ent.entity_key,
            name=ent.name,
            description=ent.description,
            confidence=ent.confidence,
            review_status="approved",
            metadata_json=json.dumps(ent.metadata or {}, ensure_ascii=False),
        )
        db.add(row)
        db.flush()
        created_e += 1
        key_to_id[ent.entity_key] = row.id
        return row.id

    for ent in entities:
        _ensure_entity(ent)

    for rel in relations:
        from_id = key_to_id.get(rel.from_key)
        to_id = key_to_id.get(rel.to_key)
        if not from_id or not to_id:
            continue
        exists = db.scalar(select(KnowledgeRelation.id).where(
            KnowledgeRelation.project_id == pid,
            KnowledgeRelation.from_entity_id == from_id,
            KnowledgeRelation.to_entity_id == to_id,
            KnowledgeRelation.relation_type == rel.relation_type,
        ))
        if exists:
            skipped_r += 1
            continue
        db.add(KnowledgeRelation(
            project_id=pid,
            from_entity_id=from_id,
            relation_type=rel.relation_type,
            to_entity_id=to_id,
            confidence=rel.confidence,
            review_status="approved",
            metadata_json=json.dumps({"evidence": rel.evidence}, ensure_ascii=False),
        ))
        created_r += 1

    db.flush()
    total_e = db.scalar(select(func.count()).select_from(KnowledgeEntity).where(KnowledgeEntity.project_id == pid)) or 0
    total_r = db.scalar(select(func.count()).select_from(KnowledgeRelation).where(KnowledgeRelation.project_id == pid)) or 0
    return {
        "created_entities": created_e,
        "created_relations": created_r,
        "skipped_entities": skipped_e,
        "skipped_relations": skipped_r,
        "total_entities": total_e,
        "total_relations": total_r,
    }


def get_hierarchy_view(
    db: Session,
    project_id: int,
    release_bundle_id: int | None = None,
    max_depth: int = 4,
):
    """项目球层级图谱（Batch 181 P2-10：路由层 ORM 收敛，逻辑整体下移）。

    返回 None 表示指定 release_bundle 不存在或不属于该项目（路由据此返回 404）；
    项目无任何发布包时返回空视图（project_name="无发布包"）。
    """
    from app.models.project import Project
    from app.models.release_bundle import ReleaseBundle
    from app.models.requirement_module import ModuleAdminLink, RequirementModule
    from app.schemas.release_bundle import ProjectSphereEdge, ProjectSphereNode, ProjectSphereView

    pid = project_id

    # Determine which bundle to use
    bundle = None
    if release_bundle_id:
        bundle = db.get(ReleaseBundle, release_bundle_id)
        if not bundle or bundle.project_id != pid:
            return None
    else:
        # Use latest active bundle
        bundle = db.scalar(
            select(ReleaseBundle)
            .where(ReleaseBundle.project_id == pid, ReleaseBundle.status == "active")
            .order_by(ReleaseBundle.id.desc())
        )
        if not bundle:
            # Fall back to latest draft
            bundle = db.scalar(
                select(ReleaseBundle)
                .where(ReleaseBundle.project_id == pid)
                .order_by(ReleaseBundle.id.desc())
            )

    if not bundle:
        return ProjectSphereView(project_id=pid, project_name="无发布包")

    project = db.get(Project, pid)
    project_name = project.name if project else f"Project #{pid}"

    # Load all modules for this bundle
    all_modules = list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.release_bundle_id == bundle.id,
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())

    nodes: list[ProjectSphereNode] = []
    edges: list[ProjectSphereEdge] = []

    # ── Node: Project ──
    project_node_id = f"project:{pid}"
    nodes.append(ProjectSphereNode(
        id=project_node_id, name=project_name, node_type="project",
    ))

    # ── Node: Version (bundle) ──
    if max_depth >= 2:
        bundle_node_id = f"bundle:{bundle.id}"
        nodes.append(ProjectSphereNode(
            id=bundle_node_id, name=bundle.name, node_type="version",
            parent_id=project_node_id,
            version=f"{bundle.client_version} / {bundle.admin_version}",
            metadata={"client_version": bundle.client_version, "admin_version": bundle.admin_version,
                       "status": bundle.status, "release_date": str(bundle.release_date) if bundle.release_date else ""},
        ))
        edges.append(ProjectSphereEdge(
            source=project_node_id, target=bundle_node_id,
            relation_type="contains", label="发布版本",
        ))

        # ── Nodes: Platforms ──
        platforms_seen: set[str] = set()
        top_modules = [m for m in all_modules if m.parent_module_id is None and m.node_type == "module"]

        if max_depth >= 3:
            for mod in top_modules:
                plat = mod.platform or "通用"
                plat_node_id = f"platform:{bundle.id}:{plat}"
                if plat not in platforms_seen:
                    platforms_seen.add(plat)
                    nodes.append(ProjectSphereNode(
                        id=plat_node_id, name=f"{plat}端", node_type="platform",
                        parent_id=bundle_node_id, platform=plat,
                    ))
                    edges.append(ProjectSphereEdge(
                        source=bundle_node_id, target=plat_node_id,
                        relation_type="contains", label="平台",
                    ))

            # ── Nodes: Modules + Pages ──
            if max_depth >= 4:
                # Build parent index
                children_by_parent: dict[int, list[RequirementModule]] = {}
                for m in all_modules:
                    if m.parent_module_id:
                        children_by_parent.setdefault(m.parent_module_id, []).append(m)

                for mod in top_modules:
                    plat = mod.platform or "通用"
                    plat_node_id = f"platform:{bundle.id}:{plat}"
                    mod_node_id = f"module:{mod.id}"

                    nodes.append(ProjectSphereNode(
                        id=mod_node_id, name=mod.name, node_type="module",
                        parent_id=plat_node_id, platform=plat,
                        version=bundle.client_version,
                        change_type=mod.change_type,
                        metadata={"description": (mod.description or "")[:200]},
                    ))
                    edges.append(ProjectSphereEdge(
                        source=plat_node_id, target=mod_node_id,
                        relation_type="contains", label="模块",
                    ))

                    # Add pages (depth >= 5)
                    if max_depth >= 5:
                        for page in children_by_parent.get(mod.id, []):
                            if page.node_type == "page":
                                page_node_id = f"page:{page.id}"
                                nodes.append(ProjectSphereNode(
                                    id=page_node_id, name=page.name, node_type="page",
                                    parent_id=mod_node_id, platform=plat,
                                    version=bundle.client_version,
                                    change_type=page.change_type,
                                ))
                                edges.append(ProjectSphereEdge(
                                    source=mod_node_id, target=page_node_id,
                                    relation_type="contains", label="页面",
                                ))

        # Also add standalone pages and attachments
        standalone = [m for m in all_modules if m.parent_module_id is None
                      and m.node_type in ("page", "attachment")]
        for m in standalone:
            plat = m.platform or "通用"
            plat_node_id = f"platform:{bundle.id}:{plat}"
            node_id = f"{m.node_type}:{m.id}"
            nodes.append(ProjectSphereNode(
                id=node_id, name=m.name, node_type=m.node_type,
                parent_id=plat_node_id, platform=plat,
                version=bundle.client_version,
            ))
            edges.append(ProjectSphereEdge(
                source=plat_node_id, target=node_id,
                relation_type="contains", label=m.node_type,
            ))

    # ── Edges: Configures (cross-system) ──
    module_ids = [m.id for m in all_modules]
    if module_ids:
        admin_links = list(db.scalars(
            select(ModuleAdminLink).where(
                ModuleAdminLink.project_id == pid,
                ModuleAdminLink.client_module_id.in_(module_ids),
            )
        ).all())
        for link in admin_links:
            admin_mod = db.get(RequirementModule, link.admin_module_id)
            edges.append(ProjectSphereEdge(
                source=f"admin_module:{link.admin_module_id}",
                target=f"module:{link.client_module_id}",
                relation_type="configures",
                confidence=link.confidence,
                label=f"配置 → {admin_mod.name if admin_mod else '#' + str(link.admin_module_id)}",
            ))

    # ── Edges: tested_by ──
    # Get tested_by relations where the target entity corresponds to our modules
    module_entity_map: dict[int, int] = {}
    for m in all_modules:
        entity = db.scalar(
            select(KnowledgeEntity).where(
                KnowledgeEntity.project_id == pid,
                KnowledgeEntity.entity_type == "client_module",
                KnowledgeEntity.name == m.name,
            )
        )
        if entity:
            module_entity_map[entity.id] = m.id

    if module_entity_map:
        test_rels = list(db.scalars(
            select(KnowledgeRelation).where(
                KnowledgeRelation.project_id == pid,
                KnowledgeRelation.relation_type == "tested_by",
                KnowledgeRelation.to_entity_id.in_(list(module_entity_map.keys())),
            ).limit(200)
        ).all())
        for rel in test_rels:
            mod_id = module_entity_map.get(rel.to_entity_id)
            if mod_id:
                edges.append(ProjectSphereEdge(
                    source=f"test_case_entity:{rel.from_entity_id}",
                    target=f"module:{mod_id}",
                    relation_type="tested_by",
                    confidence=rel.confidence,
                    label="测试覆盖",
                ))

    # ── Stats ──
    stats = {
        "versions": 1,
        "platforms": len(platforms_seen),
        "modules": sum(1 for m in all_modules if m.node_type == "module"),
        "pages": sum(1 for m in all_modules if m.node_type == "page"),
        "attachments": sum(1 for m in all_modules if m.node_type == "attachment"),
        "configures_links": sum(1 for e in edges if e.relation_type == "configures"),
        "test_relations": sum(1 for e in edges if e.relation_type == "tested_by"),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }

    return ProjectSphereView(
        project_id=pid,
        project_name=project_name,
        nodes=nodes,
        edges=edges,
        stats=stats,
    )


# ── DSH 测试 Agent 框架：模块拓扑视图（L0 骨架对外查询面）──────────

def get_module_topology(
    db: Session,
    project_id: int,
    *,
    module: str | None = None,
    limit: int = 50,
) -> dict:
    """模块拓扑视图：模块实体 + 其下关联子实体（需求/用例/接口/设计稿）。

    供 knowledge-mcp 的 get_module_topology 与开放 API 知识查询面使用。
    聚合口径：module 实体经 contains/tested_by/links_to_admin/configures
    关系挂接的子实体（Batch 122/132 已入库），返回精简 dict（无 ORM 引用）。

    Args:
        module: 模块名/实体名子串过滤（None=全部）。
        limit: 返回模块数上限。
    """
    pid = project_id
    modules, _src = get_entities(db, pid, entity_type="module", limit=200)
    if module:
        kw = module.strip().lower()
        modules = [m for m in modules if kw in (m.name or "").lower() or kw in (m.entity_key or "").lower()]
    modules = modules[:limit]

    out: list[dict] = []
    for mod in modules:
        # 双向聚合：from=module（contains 父→子）+ to=module（tested_by 子→父）
        rels_out = get_relations(db, pid, entity_id=mod.id, limit=500)
        rels_in = get_relations(db, pid, limit=500)
        rels_in = [r for r in rels_in if r.to_entity_id == mod.id]
        children: list[dict] = []
        seen: set[tuple[int, str]] = set()
        for rel in [*rels_out, *rels_in]:
            child_id = rel.to_entity_id if rel.from_entity_id == mod.id else rel.from_entity_id
            key = (child_id, rel.relation_type)
            if key in seen:
                continue
            seen.add(key)
            child = db.get(KnowledgeEntity, child_id)
            if child is None or child.project_id != pid:
                continue
            children.append({
                "entity_id": child.id,
                "entity_type": child.entity_type,
                "name": child.name,
                "entity_key": child.entity_key,
                "relation_type": rel.relation_type,
                "confidence": rel.confidence,
            })
        out.append({
            "module_id": mod.id,
            "module_key": mod.entity_key,
            "module": mod.name,
            "description": mod.description or "",
            "confidence": mod.confidence,
            "related": children,
        })
    return {"project_id": pid, "total": len(out), "modules": out}
