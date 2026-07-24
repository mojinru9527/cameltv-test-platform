"""ConfiguresLinker — 跨系统配置链路关联器 (v1.3)

Extracts configures relationships between client modules and admin modules.

A "configures" relationship means: the admin module's configuration settings
control the runtime behavior of the client module. For example:
  - 运营后台「资讯分类配置」→ configures → 用户端「资讯列表」(分类Tab显示)
  - 运营后台「推荐位管理」→ configures → 用户端「首页」(推荐内容)

Extraction strategy (3-tier):
  P1 — AI semantic analysis: parse page_interactions with interaction_type="dynamic_filter"
       and extract admin_config_source → match to admin modules
  P2 — Module name similarity: fuzzy match between client and admin module names
  P3 — Manual: user creates link in version panorama UI (not handled here)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.release_bundle import ReleaseBundle

logger = logging.getLogger("knowledge.configures_linker")


# ── Dataclasses ──

@dataclass
class ConfiguresSuggestion:
    """A suggested configures relationship."""
    client_module_id: int
    client_module_name: str
    admin_module_id: int | None = None
    admin_module_name: str = ""
    config_items: list[str] = field(default_factory=list)
    impact: str = ""
    confidence: float = 0.0
    source: str = ""  # extraction strategy used
    evidence: str = ""


@dataclass
class ConfiguresResult:
    """Result of a configures linking run."""
    suggestions: list[ConfiguresSuggestion] = field(default_factory=list)
    links_created: int = 0
    by_strategy: dict[str, int] = field(default_factory=dict)
    unmatched_admin_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Entity Key Helpers ──

def _client_module_key(project_id: int, name: str, version: str = "") -> str:
    if version:
        return f"client_module:p{project_id}:{version}:{name}"
    return f"client_module:p{project_id}:{name}"


def _admin_module_key(project_id: int, name: str, admin_version: str = "") -> str:
    if admin_version:
        return f"admin_module:p{project_id}:{admin_version}:{name}"
    return f"admin_module:p{project_id}:{name}"


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


# ── P1: Extract from dynamic_filter interactions ──

def _extract_from_dynamic_filters(
    db: Session,
    client_modules: list[RequirementModule],
    admin_modules: list[RequirementModule],
    project_id: int,
) -> list[ConfiguresSuggestion]:
    """P1 — Scan page_interactions for dynamic_filter entries with admin_config_source.

    Each page_interaction with type="dynamic_filter" and a non-empty
    admin_config_source is a strong signal of a configures relationship.
    """
    suggestions: list[ConfiguresSuggestion] = []

    # Index admin modules by normalized name
    admin_by_name: dict[str, RequirementModule] = {}
    for am in admin_modules:
        admin_by_name[_normalize(am.name)] = am

    for cm in client_modules:
        if cm.node_type != "page":
            continue

        interactions = _parse_json(cm.page_interactions)
        for item in interactions:
            if item.get("interaction_type") != "dynamic_filter":
                continue

            admin_source = item.get("admin_config_source", "")
            if not admin_source:
                continue

            # Try exact match against admin module names
            admin_mod = admin_by_name.get(_normalize(admin_source))
            if admin_mod is None:
                # Fuzzy: check if any admin module name is contained in admin_config_source
                for name, mod in admin_by_name.items():
                    if name in _normalize(admin_source) or _normalize(admin_source) in name:
                        admin_mod = mod
                        break

            if admin_mod:
                # Find parent client module
                client_mod = _get_parent_module(db, cm)

                suggestions.append(ConfiguresSuggestion(
                    client_module_id=client_mod.id if client_mod else cm.id,
                    client_module_name=client_mod.name if client_mod else cm.name,
                    admin_module_id=admin_mod.id,
                    admin_module_name=admin_mod.name,
                    config_items=[item.get("source_element", "")],
                    impact=item.get("description", f"控制{cm.name}中的{item.get('trigger', '')}"),
                    confidence=0.85,
                    source="dynamic_filter",
                    evidence=json.dumps(item, ensure_ascii=False),
                ))
            else:
                # Couldn't match — record for manual review
                logger.debug(
                    "Unmatched admin_config_source '%s' for page #%d",
                    admin_source, cm.id,
                )

    return suggestions


# ── P2: Module name similarity ──

def _extract_by_similarity(
    client_modules: list[RequirementModule],
    admin_modules: list[RequirementModule],
) -> list[ConfiguresSuggestion]:
    """P2 — Fuzzy match client and admin module names for potential configures links.

    Heuristic: if a client module name is a substring of an admin module name
    (or vice versa), it's a potential configures link. Examples:
      - "资讯" ↔ "资讯分类配置"  → likely configures
      - "直播" ↔ "直播管理"      → likely configures
      - "用户" ↔ "用户数据"      → likely configures (but could also be links_to_admin)
    """
    suggestions: list[ConfiguresSuggestion] = []
    client_only = [m for m in client_modules if m.node_type == "module"]
    admin_only = [m for m in admin_modules if m.node_type == "module"]

    for cm in client_only:
        cm_name = _normalize(cm.name)
        if len(cm_name) < 2:
            continue

        for am in admin_only:
            am_name = _normalize(am.name)
            if len(am_name) < 2:
                continue

            # Check substring overlap
            if cm_name in am_name or am_name in cm_name:
                # Higher confidence for shorter overlap ratio
                overlap_ratio = len(cm_name) / max(1, len(am_name))
                confidence = 0.5 + overlap_ratio * 0.3

                suggestions.append(ConfiguresSuggestion(
                    client_module_id=cm.id,
                    client_module_name=cm.name,
                    admin_module_id=am.id,
                    admin_module_name=am.name,
                    config_items=[],
                    impact=f"{am.name} 配置可能影响 {cm.name} 的展示内容",
                    confidence=min(0.7, confidence),
                    source="name_similarity",
                    evidence=f"模块名相似: '{cm.name}' ↔ '{am.name}'",
                ))

    return suggestions


# ── Helpers ──

def _parse_json(text: str) -> list[dict]:
    try:
        return json.loads(text or "[]")
    except json.JSONDecodeError:
        return []


def _get_parent_module(db: Session, page: RequirementModule) -> RequirementModule | None:
    """Get the parent module of a page node."""
    if page.parent_module_id:
        return db.get(RequirementModule, page.parent_module_id)
    return None


# ── Public API ──

def suggest_configures_links(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    client_version: str = "",
    admin_version: str = "",
) -> ConfiguresResult:
    """Analyze a release bundle and suggest configures relationships.

    Returns a ConfiguresResult with ranked suggestions for human review.
    """
    result = ConfiguresResult()

    # Load bundle
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if not bundle:
        result.warnings.append(f"Release bundle #{release_bundle_id} not found")
        return result

    # Load all modules in bundle
    all_modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
            )
        ).all()
    )

    # Separate client vs admin modules
    client_modules = [m for m in all_modules if m.platform in ("APP", "PC", "WEB", "")]
    admin_modules = [m for m in all_modules if m.platform == "ADMIN"]

    if not client_modules or not admin_modules:
        result.warnings.append(
            f"Need both client ({len(client_modules)}) and admin ({len(admin_modules)}) modules"
        )
        return result

    # P1: dynamic_filter extraction
    p1_suggestions = _extract_from_dynamic_filters(
        db, client_modules, admin_modules, project_id,
    )
    result.by_strategy["dynamic_filter"] = len(p1_suggestions)
    result.suggestions.extend(p1_suggestions)

    # Collect unmatched admin sources
    {s.admin_module_id for s in p1_suggestions if s.admin_module_id}
    for page in client_modules:
        if page.node_type != "page":
            continue
        for item in _parse_json(page.page_interactions):
            if item.get("interaction_type") == "dynamic_filter" and item.get("admin_config_source"):
                # Check if this source is already matched
                source = item["admin_config_source"]
                matched = any(
                    _normalize(source) in _normalize(s.admin_module_name)
                    or _normalize(s.admin_module_name) in _normalize(source)
                    for s in p1_suggestions
                )
                if not matched and source not in result.unmatched_admin_sources:
                    result.unmatched_admin_sources.append(source)

    # P2: name similarity (for modules not already covered by P1)
    covered_client_ids = {s.client_module_id for s in p1_suggestions}
    uncovered_client = [m for m in client_modules if m.id not in covered_client_ids]
    p2_suggestions = _extract_by_similarity(uncovered_client, admin_modules)

    # Filter out duplicates from P1
    for s in p2_suggestions:
        is_dup = any(
            s2.client_module_id == s.client_module_id
            and s2.admin_module_id == s.admin_module_id
            for s2 in p1_suggestions
        )
        if not is_dup:
            result.suggestions.append(s)

    result.by_strategy["name_similarity"] = len(p2_suggestions)

    # Sort by confidence descending
    result.suggestions.sort(key=lambda s: s.confidence, reverse=True)

    logger.info(
        "Configures linking: %d suggestions (P1=%d, P2=%d) for bundle #%d",
        len(result.suggestions),
        result.by_strategy.get("dynamic_filter", 0),
        result.by_strategy.get("name_similarity", 0),
        release_bundle_id,
    )

    return result


def confirm_configures_links(
    db: Session,
    *,
    suggestions: list[ConfiguresSuggestion],
    project_id: int,
    client_version: str = "",
    admin_version: str = "",
) -> ConfiguresResult:
    """Confirm and persist configures links as ModuleAdminLink + KnowledgeRelation.

    Only creates entries for suggestions with admin_module_id set.
    """
    result = ConfiguresResult(suggestions=suggestions)

    for s in suggestions:
        if not s.admin_module_id:
            continue
        if s.confidence < 0.5:
            continue

        # 1. Create ModuleAdminLink
        existing_link = db.scalar(
            select(ModuleAdminLink.id).where(
                ModuleAdminLink.project_id == project_id,
                ModuleAdminLink.client_module_id == s.client_module_id,
                ModuleAdminLink.admin_module_id == s.admin_module_id,
                ModuleAdminLink.relation_type == "configures",
            )
        )
        if not existing_link:
            link = ModuleAdminLink(
                project_id=project_id,
                client_module_id=s.client_module_id,
                admin_module_id=s.admin_module_id,
                relation_type="configures",
                confidence=s.confidence,
                evidence=s.evidence,
                metadata_json=json.dumps({
                    "config_items": s.config_items,
                    "impact": s.impact,
                    "source": s.source,
                }, ensure_ascii=False),
            )
            db.add(link)

        # 2. Create KnowledgeRelation
        client_key = _client_module_key(project_id, s.client_module_name, client_version)
        admin_key = _admin_module_key(project_id, s.admin_module_name, admin_version)

        client_entity = _ensure_entity(db, project_id, client_key, "client_module", s.client_module_name)
        admin_entity = _ensure_entity(db, project_id, admin_key, "admin_module", s.admin_module_name)

        if client_entity and admin_entity:
            rel_exists = db.scalar(
                select(KnowledgeRelation.id).where(
                    KnowledgeRelation.project_id == project_id,
                    KnowledgeRelation.from_entity_id == client_entity.id,
                    KnowledgeRelation.to_entity_id == admin_entity.id,
                    KnowledgeRelation.relation_type == "configures",
                )
            )
            if not rel_exists:
                rel = KnowledgeRelation(
                    project_id=project_id,
                    from_entity_id=client_entity.id,
                    relation_type="configures",
                    to_entity_id=admin_entity.id,
                    confidence=s.confidence,
                    metadata_json=json.dumps({
                        "config_items": s.config_items,
                        "impact": s.impact,
                        "source": s.source,
                    }, ensure_ascii=False),
                )
                db.add(rel)
                result.links_created += 1

    db.flush()
    logger.info("Confirmed %d configures links for project #%d", result.links_created, project_id)
    return result


def _ensure_entity(
    db: Session, project_id: int, entity_key: str,
    entity_type: str, name: str,
) -> KnowledgeEntity | None:
    """Get or create a KnowledgeEntity."""
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == entity_key,
        )
    )
    if entity:
        return entity

    entity = KnowledgeEntity(
        project_id=project_id,
        entity_type=entity_type,
        entity_key=entity_key,
        name=name,
        description=f"{entity_type}: {name}",
        confidence=0.8,
    )
    db.add(entity)
    db.flush()
    return entity
