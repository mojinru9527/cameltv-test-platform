"""知识图谱实体提取服务（M3）

从 knowledge_chunk 中提取结构化实体（API/参数/错误码/需求/缺陷/用例）并写入 knowledge_entity。
提取策略：规则驱动（正则 + 字段解析），不依赖外部 LLM（速度、成本、确定性）。
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any

from sqlalchemy import select

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
            KnowledgeChunk.status == "active",
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
