"""知识图谱 auto-build 服务（M3）

从 ReleaseBundle → RequirementModule tree 出发，构建层级实体和关系，
持久化到 knowledge_entity / knowledge_relation，实现跨会话累积的版本谱系图。

遵循 entity_key 约定（batch-27 design doc §1.6）：
  release_bundle:{name}:{version}
  platform:{name}:{version}:{platform}
  client_module:{name}:{version}:{platform}:{module_name}
  admin_module:{name}:{version}:{module_name}
  page:{name}:{version}:{platform}:{module_name}:{page_name}
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import ModuleAdminLink, RequirementModule

logger = logging.getLogger("knowledge.graph_builder")


@dataclass
class AutoBuildResult:
    created_entities: int = 0
    created_relations: int = 0
    skipped_entities: int = 0
    skipped_relations: int = 0
    message: str = ""


# ── entity_key 构建 ──

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


def _rel_exists(db, project_id: int, from_id: int, to_id: int, rel_type: str) -> bool:
    return db.scalar(
        select(KnowledgeRelation.id).where(
            KnowledgeRelation.project_id == project_id,
            KnowledgeRelation.from_entity_id == from_id,
            KnowledgeRelation.to_entity_id == to_id,
            KnowledgeRelation.relation_type == rel_type,
        )
    ) is not None


def _ensure_entity(
    db,
    project_id: int,
    entity_type: str,
    entity_key: str,
    name: str,
    description: str = "",
    source_id: int | None = None,
    business_ref_type: str = "",
    business_ref_id: int | None = None,
    confidence: float = 1.0,
    metadata_json: str = "{}",
    review_status: str = "approved",
) -> tuple[KnowledgeEntity, bool]:
    """幂等创建实体。返回 (entity, is_new)。"""
    existing = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == entity_key,
        )
    )
    if existing:
        return existing, False

    entity = KnowledgeEntity(
        project_id=project_id,
        entity_type=entity_type,
        entity_key=entity_key,
        name=name,
        description=description,
        source_id=source_id,
        business_ref_type=business_ref_type,
        business_ref_id=business_ref_id,
        confidence=confidence,
        review_status=review_status,
        metadata_json=metadata_json,
    )
    db.add(entity)
    db.flush()  # 获取 id
    return entity, True


def _ensure_relation(
    db,
    project_id: int,
    from_entity_id: int,
    relation_type: str,
    to_entity_id: int,
    confidence: float = 1.0,
    evidence_chunk_ids: str = "[]",
    review_status: str = "approved",
) -> tuple[KnowledgeRelation | None, bool]:
    """幂等创建关系。返回 (relation, is_new)。"""
    if _rel_exists(db, project_id, from_entity_id, to_entity_id, relation_type):
        return None, False

    rel = KnowledgeRelation(
        project_id=project_id,
        from_entity_id=from_entity_id,
        relation_type=relation_type,
        to_entity_id=to_entity_id,
        confidence=confidence,
        evidence_chunk_ids=evidence_chunk_ids,
        review_status=review_status,
        metadata_json="{}",
    )
    db.add(rel)
    db.flush()
    return rel, True


# ── auto-build 主入口 ──

def auto_build_graph(
    project_id: int,
    release_bundle_id: int,
    force: bool = False,
) -> AutoBuildResult:
    """从 ReleaseBundle + RequirementModule 树构建完整知识图谱。

    创建层级:
      project → release_bundle → platform → module → page

    关系:
      belongs_to_version, has_platform, has_module, has_page,
      links_to_admin, tested_by, navigates_to, configures, evolves_from
    """
    from app.core.config import settings

    if not settings.knowledge_graph_enabled:
        return AutoBuildResult(message="知识图谱未启用（knowledge_graph_enabled=False）")

    db = SessionLocal()
    result = AutoBuildResult()
    entity_map: dict[str, KnowledgeEntity] = {}  # entity_key → entity

    try:
        # 加载 ReleaseBundle
        bundle = db.get(ReleaseBundle, release_bundle_id)
        if not bundle:
            result.message = f"ReleaseBundle #{release_bundle_id} 不存在"
            return result

        bundle_name = bundle.name or f"Bundle#{bundle.id}"
        client_ver = bundle.client_version or "unknown"
        admin_ver = bundle.admin_version or "unknown"

        # ── 幂等检查：bundle entity 是否已存在 ──
        bundle_key = _entity_key("release_bundle", project_id, f"{bundle_name}:{client_ver}")
        if _entity_exists(db, project_id, bundle_key) and not force:
            result.message = f"Graph already built for release bundle '{bundle_name} v{client_ver}'. Use force=true to rebuild."
            return result

        # ── force 模式：删除已有实体和关系 ──
        if force and _entity_exists(db, project_id, bundle_key):
            _cleanup_bundle_graph(db, project_id, bundle_key)

        # ── 1. 确保 project 实体 ──
        proj_key = _entity_key("project", project_id, f"project_{project_id}")
        proj_entity, _ = _ensure_entity(
            db, project_id,
            entity_type="project",
            entity_key=proj_key,
            name=f"Project #{project_id}",
            description=f"项目知识球 #{project_id}",
            confidence=1.0,
        )
        entity_map[proj_key] = proj_entity

        # ── 2. 创建 release_bundle 实体 ──
        bundle_entity, bundle_is_new = _ensure_entity(
            db, project_id,
            entity_type="release_bundle",
            entity_key=bundle_key,
            name=f"{bundle_name} v{client_ver}",
            description=f"用户端 {client_ver} / 运营后台 {admin_ver}",
            business_ref_type="release_bundle",
            business_ref_id=bundle.id,
            confidence=1.0,
            metadata_json=json.dumps({
                "bundle_name": bundle_name,
                "client_version": client_ver,
                "admin_version": admin_ver,
                "status": bundle.status,
            }, ensure_ascii=False),
        )
        entity_map[bundle_key] = bundle_entity
        if bundle_is_new:
            result.created_entities += 1

        # ── 3. project → bundle ──
        _, rel_new = _ensure_relation(
            db, project_id,
            proj_entity.id, "contains", bundle_entity.id,
            confidence=1.0,
        )
        if rel_new:
            result.created_relations += 1

        # ── 4. 加载模块树 ──
        modules = list(db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == project_id,
                RequirementModule.release_bundle_id == release_bundle_id,
            )
        ).all())

        if not modules:
            result.message = f"No requirement modules found for bundle #{release_bundle_id}"
            db.commit()
            return result

        # ── 5. 分组并构建层级 ──
        # 按 platform 分组
        platform_modules: dict[str, list[RequirementModule]] = {}
        for m in modules:
            platform = m.platform or "UNKNOWN"
            platform_modules.setdefault(platform, []).append(m)

        # ── 5a. 创建 platform 实体 ──
        for platform_name in platform_modules:
            plat_key = _entity_key("platform", project_id, f"{bundle_name}:{client_ver}:{platform_name}")
            plat_entity, plat_is_new = _ensure_entity(
                db, project_id,
                entity_type="platform",
                entity_key=plat_key,
                name=f"{platform_name} ({bundle_name} v{client_ver})",
                description=f"平台 {platform_name} — 用户端 v{client_ver}",
                confidence=1.0,
            )
            entity_map[plat_key] = plat_entity
            if plat_is_new:
                result.created_entities += 1

            # bundle → platform (has_platform)
            _, rel_new = _ensure_relation(
                db, project_id,
                bundle_entity.id, "has_platform", plat_entity.id,
                confidence=1.0,
            )
            if rel_new:
                result.created_relations += 1

            # ── 5b. 按 parent_module_id 构建模块树 ──
            platform_mods = [m for m in platform_modules[platform_name] if m.node_type in ("module",)]
            pages = [m for m in platform_modules[platform_name] if m.node_type == "page"]

            # 区分 APP/PC/WEB（用户端 = client_module）和 ADMIN（运营后台 = admin_module）
            is_admin = platform_name.upper() == "ADMIN"
            module_type = "admin_module" if is_admin else "client_module"

            for mod in platform_mods:
                mod_key = _entity_key(
                    module_type, project_id,
                    f"{bundle_name}:{client_ver}:{platform_name}:{mod.name}",
                )
                mod_entity, mod_is_new = _ensure_entity(
                    db, project_id,
                    entity_type=module_type,
                    entity_key=mod_key,
                    name=mod.name,
                    description=mod.description or f"{platform_name} 模块: {mod.name}",
                    business_ref_type="requirement_module",
                    business_ref_id=mod.id,
                    confidence=1.0,
                    metadata_json=json.dumps({
                        "change_type": mod.change_type,
                        "lanhu_page_id": mod.lanhu_page_id,
                        "source_version": mod.source_version,
                    }, ensure_ascii=False),
                )
                entity_map[mod_key] = mod_entity
                if mod_is_new:
                    result.created_entities += 1

                # platform → module (has_module)
                _, rel_new = _ensure_relation(
                    db, project_id,
                    plat_entity.id, "has_module", mod_entity.id,
                    confidence=1.0,
                )
                if rel_new:
                    result.created_relations += 1

                # ── 5c. 找到属于此模块的页面 ──
                # page 通过 parent_module_id 关联到 module
                module_pages = [
                    p for p in pages
                    if p.parent_module_id == mod.id
                ]
                for page in module_pages:
                    page_key = _entity_key(
                        "page", project_id,
                        f"{bundle_name}:{client_ver}:{platform_name}:{mod.name}:{page.name}",
                    )
                    page_entity, page_is_new = _ensure_entity(
                        db, project_id,
                        entity_type="page",
                        entity_key=page_key,
                        name=page.name,
                        description=page.description or f"{platform_name} 页面: {page.name}",
                        business_ref_type="requirement_module",
                        business_ref_id=page.id,
                        confidence=1.0,
                        metadata_json=json.dumps({
                            "change_type": page.change_type,
                            "page_interactions": json.loads(page.page_interactions) if page.page_interactions else [],
                            "screenshot_urls": json.loads(page.screenshot_urls) if page.screenshot_urls else [],
                        }, ensure_ascii=False),
                    )
                    entity_map[page_key] = page_entity
                    if page_is_new:
                        result.created_entities += 1

                    # module → page (has_page)
                    _, rel_new = _ensure_relation(
                        db, project_id,
                        mod_entity.id, "has_page", page_entity.id,
                        confidence=1.0,
                    )
                    if rel_new:
                        result.created_relations += 1

                    # ── 6. navigates_to: page → page（从 page_interactions 解析） ──
                    interactions = json.loads(page.page_interactions) if page.page_interactions else []
                    for ia in interactions:
                        target_page_name = ia.get("target_page", "")
                        if not target_page_name:
                            continue
                        # 查找目标页面在当前 bundle 中的 entity
                        target_key = _entity_key(
                            "page", project_id,
                            f"{bundle_name}:{client_ver}:{platform_name}:{mod.name}:{target_page_name}",
                        )
                        # 也尝试搜其他模块的页面
                        if target_key not in entity_map:
                            for other_mod in platform_mods:
                                candidate_key = _entity_key(
                                    "page", project_id,
                                    f"{bundle_name}:{client_ver}:{platform_name}:{other_mod.name}:{target_page_name}",
                                )
                                if candidate_key in entity_map:
                                    target_key = candidate_key
                                    break
                        if target_key in entity_map:
                            _, rel_new = _ensure_relation(
                                db, project_id,
                                page_entity.id, "navigates_to", entity_map[target_key].id,
                                confidence=0.85,
                                evidence_chunk_ids=json.dumps([{
                                    "trigger": ia.get("trigger", ""),
                                    "interaction_type": ia.get("interaction_type", "navigation"),
                                }]),
                            )
                            if rel_new:
                                result.created_relations += 1

        # ── 7. links_to_admin / configures（从 ModuleAdminLink 表） ──
        admin_links = list(db.scalars(
            select(ModuleAdminLink).where(
                ModuleAdminLink.project_id == project_id,
            )
        ).all())

        # 过滤出与当前 bundle 模块相关的 link
        bundle_module_ids = {m.id for m in modules}
        for link in admin_links:
            if link.client_module_id not in bundle_module_ids:
                continue
            # 找到 client_module entity
            client_mod = _find_entity_by_business_ref(
                db, project_id, "requirement_module", link.client_module_id, entity_map,
            )
            admin_mod = _find_entity_by_business_ref(
                db, project_id, "requirement_module", link.admin_module_id, entity_map,
            )
            if client_mod and admin_mod:
                rel_type = link.relation_type or "links_to_admin"
                _, rel_new = _ensure_relation(
                    db, project_id,
                    client_mod.id, rel_type, admin_mod.id,
                    confidence=link.confidence or 0.8,
                    evidence_chunk_ids=json.dumps([{"evidence": link.evidence}]) if link.evidence else "[]",
                )
                if rel_new:
                    result.created_relations += 1

        # ── 8. belongs_to_version: bundle → release_bundle (self-referencing for hierarchy) ──
        _, rel_new = _ensure_relation(
            db, project_id,
            bundle_entity.id, "belongs_to_version", bundle_entity.id,
            confidence=1.0,
            evidence_chunk_ids=json.dumps([{"version": client_ver}]),
        )
        if rel_new:
            result.created_relations += 1

        # ── 9. evolves_from: 跨版本同模块演化（parent_bundle_id） ──
        if bundle.parent_bundle_id:
            parent_bundle = db.get(ReleaseBundle, bundle.parent_bundle_id)
            if parent_bundle:
                parent_modules = list(db.scalars(
                    select(RequirementModule).where(
                        RequirementModule.project_id == project_id,
                        RequirementModule.release_bundle_id == parent_bundle.id,
                    )
                ).all())
                for mod in modules:
                    if mod.parent_module_id:
                        # 该模块有 parent_module_id 指向旧版本的同一模块
                        matched = [
                            pm for pm in parent_modules
                            if pm.id == mod.parent_module_id
                        ]
                        if matched:
                            mod_key = _entity_key(
                                "client_module", project_id,
                                f"{bundle_name}:{client_ver}:{mod.platform or 'UNKNOWN'}:{mod.name}",
                            )
                            parent_mod_key = _entity_key(
                                "client_module", project_id,
                                f"{parent_bundle.name or 'Unknown'}:{parent_bundle.client_version or 'unknown'}:{mod.platform or 'UNKNOWN'}:{mod.name}",
                            )
                            if mod_key in entity_map and parent_mod_key in entity_map:
                                _, rel_new = _ensure_relation(
                                    db, project_id,
                                    entity_map[mod_key].id, "evolves_from", entity_map[parent_mod_key].id,
                                    confidence=0.9,
                                    evidence_chunk_ids=json.dumps([{
                                        "from_version": parent_bundle.client_version,
                                        "to_version": client_ver,
                                    }]),
                                )
                                if rel_new:
                                    result.created_relations += 1

        # ── 10. 创建 changelog_entry 实体（如果模块有变更类型） ──
        for mod in modules:
            if mod.change_type and mod.change_type != "unchanged":
                changelog_key = _entity_key(
                    "changelog_entry", project_id,
                    f"{bundle_name}:{client_ver}:{mod.platform or 'UNKNOWN'}:{mod.name}",
                )
                changelog_entity, cl_is_new = _ensure_entity(
                    db, project_id,
                    entity_type="changelog_entry",
                    entity_key=changelog_key,
                    name=f"{mod.change_type}: {mod.name} ({client_ver})",
                    description=f"变更条目: {mod.name} — {mod.change_type}",
                    confidence=0.9,
                    metadata_json=json.dumps({
                        "change_type": mod.change_type,
                        "version": client_ver,
                        "platform": mod.platform,
                    }, ensure_ascii=False),
                )
                if cl_is_new:
                    result.created_entities += 1

                # 关联到 module entity
                mod_key = _entity_key(
                    "client_module" if mod.platform != "ADMIN" else "admin_module",
                    project_id,
                    f"{bundle_name}:{client_ver}:{mod.platform or 'UNKNOWN'}:{mod.name}",
                )
                if mod_key in entity_map:
                    _, rel_new = _ensure_relation(
                        db, project_id,
                        changelog_entity.id, "described_by", entity_map[mod_key].id,
                        confidence=0.85,
                    )
                    if rel_new:
                        result.created_relations += 1

        db.commit()

        result.message = (
            f"Graph built for '{bundle_name} v{client_ver}': "
            f"{result.created_entities} entities, {result.created_relations} relations created"
        )
        logger.info(
            "auto_build_graph bundle=%d: %d entities, %d relations",
            release_bundle_id, result.created_entities, result.created_relations,
        )
        return result

    except Exception:
        db.rollback()
        logger.exception("auto_build_graph failed for bundle %d", release_bundle_id)
        raise


def _cleanup_bundle_graph(db, project_id: int, bundle_key: str) -> None:
    """force 模式下清理已存在的实体和关系。"""
    bundle_entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == bundle_key,
        )
    )
    if not bundle_entity:
        return
    # 删除与 bundle 关联的所有关系
    db.execute(
        select(KnowledgeRelation).where(
            KnowledgeRelation.project_id == project_id,
            (KnowledgeRelation.from_entity_id == bundle_entity.id) |
            (KnowledgeRelation.to_entity_id == bundle_entity.id),
        )
    )
    # 简单起见，这里采用级联删除：删除包含 bundle_name 的 entity_key
    from sqlalchemy import delete
    import re
    bundle_name_part = bundle_key.split(":p")[0]  # release_bundle:name:version
    # 更精确的删除：找出该 bundle 的所有层级实体
    entities_to_delete = db.scalars(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key.like(f"%{bundle_name_part}%"),
        )
    ).all()
    for e in entities_to_delete:
        # 删除关联关系
        stmt = delete(KnowledgeRelation).where(
            KnowledgeRelation.project_id == project_id,
            (KnowledgeRelation.from_entity_id == e.id) |
            (KnowledgeRelation.to_entity_id == e.id),
        )
        db.execute(stmt)
        db.delete(e)
    db.flush()


def _find_entity_by_business_ref(
    db, project_id: int, business_ref_type: str, business_ref_id: int,
    entity_map: dict[str, KnowledgeEntity] | None = None,
) -> KnowledgeEntity | None:
    """通过业务引用查找 entity，先在 entity_map 中查找，再查 DB。"""
    if entity_map:
        for entity in entity_map.values():
            if (entity.business_ref_type == business_ref_type and
                    entity.business_ref_id == business_ref_id):
                return entity
    return db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.business_ref_type == business_ref_type,
            KnowledgeEntity.business_ref_id == business_ref_id,
        )
    )
