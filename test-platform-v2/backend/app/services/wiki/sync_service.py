"""Wiki 同步服务 — 蓝湖模块树 → Wiki 目录结构映射 + 差异对比

Maps a ReleaseBundle's RequirementModule tree to Wiki pages for RAG baseline
synchronization and diff comparison.

Mapping rules:
  - Root: /{project_name}/
  - Platform folders: /{project_name}/{APP|PC|WEB|ADMIN}/
  - Modules: /{project_name}/{platform}/{module_name}/
  - Pages: /{project_name}/{platform}/{module_name}/{page_name}/
  - Attachments: /{project_name}/说明附件/{file_name}/

Each page creates a WikiRawSource entry (immutable fact layer).
The raw source content = OCR text from evidence + module description.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lanhu_evidence import LanhuEvidencePage
from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle
from app.models.wiki import WikiRawSource
from app.services.knowledge.sanitize import sanitize

logger = logging.getLogger("wiki.sync")


# ── Dataclasses ──

@dataclass
class WikiSyncResult:
    """Result of a sync operation."""
    release_bundle_id: int
    raw_sources_created: int = 0
    raw_sources_updated: int = 0
    raw_sources_skipped: int = 0
    wiki_pages_created: int = 0
    wik_pages_synced: int = 0
    coverage: dict = field(default_factory=dict)  # {total_pages, synced_pages, missing_pages}
    errors: list[str] = field(default_factory=list)


@dataclass
class WikiTreeNode:
    """A node in the Wiki directory tree."""
    path: str  # e.g. "/体育平台/APP端/资讯/资讯列表"
    title: str
    page_type: str  # module | page | attachment | changelog
    children: list[WikiTreeNode] = field(default_factory=list)
    module_id: int | None = None
    content_preview: str = ""  # first 200 chars of content


# ── Constants ──

_PROJECT_NAME = "体育平台"  # default; could be parameterized per project_id

_PAGE_TYPE_MAP = {
    "module": "module",
    "page": "requirement",
    "attachment": "attachment",
    "function_point": "requirement",
}


# ── Content Hash ──

def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# ── Build Wiki Tree ──

def build_wiki_tree(
    db: Session,
    *,
    release_bundle_id: int,
    project_name: str = _PROJECT_NAME,
) -> list[WikiTreeNode]:
    """Build a Wiki directory tree from a ReleaseBundle's module tree.

    Returns the tree root nodes (platform-level folders).
    """
    # Load bundle
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if not bundle:
        logger.warning("Release bundle #%d not found", release_bundle_id)
        return []

    # Load all modules
    modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
            ).order_by(RequirementModule.id)
        ).all()
    )

    if not modules:
        return []

    # Separate top-level modules (no parent) from sub-nodes
    top_modules = [m for m in modules if m.parent_module_id is None and m.node_type == "module"]
    child_nodes = [m for m in modules if m.parent_module_id is not None]

    # Index children by parent_module_id
    children_by_parent: dict[int, list[RequirementModule]] = {}
    for child in child_nodes:
        children_by_parent.setdefault(child.parent_module_id, []).append(child)

    # Build tree recursively
    root_nodes: list[WikiTreeNode] = []

    for mod in top_modules:
        platform = mod.platform or "通用"
        module_path = f"/{project_name}/{platform}/{mod.name}"
        node = _build_node_recursive(mod, module_path, children_by_parent)
        root_nodes.append(node)

    # Add attachments as a separate root folder
    attachments = [m for m in modules if m.node_type == "attachment"]
    if attachments:
        att_root = WikiTreeNode(
            path=f"/{project_name}/说明附件",
            title="说明附件",
            page_type="module",
        )
        for att in attachments:
            att_root.children.append(WikiTreeNode(
                path=f"/{project_name}/说明附件/{att.name}",
                title=att.name,
                page_type="attachment",
                module_id=att.id,
                content_preview=(att.description or att.name)[:200],
            ))
        root_nodes.append(att_root)

    return root_nodes


def _build_node_recursive(
    mod: RequirementModule,
    path_prefix: str,
    children_by_parent: dict[int, list[RequirementModule]],
) -> WikiTreeNode:
    """Recursively build WikiTreeNode from a RequirementModule."""
    node = WikiTreeNode(
        path=path_prefix,
        title=mod.name,
        page_type=_PAGE_TYPE_MAP.get(mod.node_type, "requirement"),
        module_id=mod.id,
        content_preview=(
            sanitize(mod.description or mod.name)[:200]
            if mod.description else ""
        ),
    )

    # Add child nodes
    for child in children_by_parent.get(mod.id, []):
        child_path = f"{path_prefix}/{child.name}"
        child_node = _build_node_recursive(child, child_path, children_by_parent)
        node.children.append(child_node)

    return node


# ── Sync to Wiki ──

def sync_to_wiki(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    project_name: str = _PROJECT_NAME,
    create_wiki_pages: bool = False,
) -> WikiSyncResult:
    """Sync a release bundle's module tree to Wiki Raw Sources.

    For each page in the module tree:
      1. Build Wiki path (directory structure).
      2. Collect OCR content from LanhuEvidencePage.
      3. Create/update WikiRawSource (immutable version = release_bundle_id:module_id).
      4. Optionally create WikiPage for LLM compilation.

    Args:
        create_wiki_pages: If True, also trigger WikiPage creation (requires ingest job).

    Returns:
        WikiSyncResult with creation/update counts and coverage stats.
    """
    result = WikiSyncResult(release_bundle_id=release_bundle_id)

    # Load bundle
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if not bundle:
        result.errors.append(f"Release bundle #{release_bundle_id} not found")
        return result

    # Load all page-type modules
    pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type.in_(["page", "attachment"]),
            )
        ).all()
    )

    result.coverage["total_pages"] = len(pages)

    # Build evidence page index
    evidence_pages = list(
        db.scalars(
            select(LanhuEvidencePage).where(
                LanhuEvidencePage.project_id == project_id,
            )
        ).all()
    )
    evidence_by_page_id: dict[str, LanhuEvidencePage] = {
        ep.page_id: ep for ep in evidence_pages if ep.page_id
    }

    # Build module tree for path resolution
    all_modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
            )
        ).all()
    )
    module_by_id: dict[int, RequirementModule] = {m.id: m for m in all_modules}

    synced_count = 0
    skipped_count = 0
    updated_count = 0

    for page in pages:
        try:
            # Resolve full path
            wiki_path = _resolve_path(page, module_by_id, project_name)
            wiki_title = page.name

            # Collect content
            content_parts: list[str] = []

            # From evidence page OCR
            if page.lanhu_page_id and page.lanhu_page_id in evidence_by_page_id:
                ep = evidence_by_page_id[page.lanhu_page_id]
                if ep.merged_text:
                    content_parts.append(ep.merged_text)
                elif ep.ocr_text:
                    content_parts.append(ep.ocr_text)

            # From module description
            if page.description:
                content_parts.append(page.description)

            # From page interactions (as structured appendix)
            if page.page_interactions and page.page_interactions != "[]":
                try:
                    interactions = json.loads(page.page_interactions)
                    if interactions:
                        content_parts.append("\n## 页面交互跳转\n")
                        for inter in interactions:
                            content_parts.append(
                                f"- {inter.get('trigger', '')} → {inter.get('target_page', '')}"
                                f" ({inter.get('interaction_type', 'navigation')})"
                            )
                except json.JSONDecodeError:
                    pass

            content_md = "\n\n".join(content_parts) if content_parts else f"# {page.name}\n\n（无 OCR 内容）"
            chash = _content_hash(content_md)

            # Immutable version key: bundle_id:module_id
            immutable_version = f"bundle:{release_bundle_id}:module:{page.id}"

            # Check existing
            existing = db.scalar(
                select(WikiRawSource).where(
                    WikiRawSource.project_id == project_id,
                    WikiRawSource.immutable_version == immutable_version,
                    WikiRawSource.content_hash == chash,
                )
            )
            if existing:
                skipped_count += 1
                continue

            # Check if content changed (supersede old)
            old_active = db.scalar(
                select(WikiRawSource).where(
                    WikiRawSource.project_id == project_id,
                    WikiRawSource.immutable_version == immutable_version,
                    WikiRawSource.status == "active",
                )
            )
            if old_active:
                old_active.status = "superseded"
                updated_count += 1

            # Create WikiRawSource
            raw_source = WikiRawSource(
                project_id=project_id,
                source_type="requirement",
                source_ref=wiki_path,
                title=sanitize(wiki_title)[:500],
                content_md=sanitize(content_md),
                content_hash=chash,
                immutable_version=immutable_version,
                business_ref_type="requirement_module",
                business_ref_id=page.id,
                metadata_json=json.dumps({
                    "wiki_path": wiki_path,
                    "release_bundle_id": release_bundle_id,
                    "client_version": bundle.client_version,
                    "admin_version": bundle.admin_version,
                    "module_name": page.name,
                    "node_type": page.node_type,
                    "platform": page.platform,
                    "synced_at": datetime.now().isoformat(),
                }, ensure_ascii=False),
                status="active",
            )
            db.add(raw_source)
            synced_count += 1

        except Exception as e:
            logger.exception("Failed to sync page #%d '%s' to Wiki", page.id, page.name)
            result.errors.append(f"Page #{page.id} '{page.name}': {e}")

    result.raw_sources_created = synced_count
    result.raw_sources_updated = updated_count
    result.raw_sources_skipped = skipped_count
    result.coverage["synced_pages"] = synced_count
    result.coverage["missing_pages"] = len(pages) - synced_count - skipped_count

    db.flush()

    logger.info(
        "Wiki sync for bundle #%d: %d created, %d updated, %d skipped, %d errors",
        release_bundle_id, synced_count, updated_count, skipped_count, len(result.errors),
    )

    return result


# ── Path Resolution ──

def _resolve_path(
    page: RequirementModule,
    module_by_id: dict[int, RequirementModule],
    project_name: str,
) -> str:
    """Resolve the full Wiki path for a module node by walking up the parent chain."""
    parts: list[str] = [page.name]

    current = page
    while current.parent_module_id and current.parent_module_id in module_by_id:
        parent = module_by_id[current.parent_module_id]
        parts.append(parent.name)
        current = parent

    # Reverse to get root→leaf order
    parts.reverse()

    # Prefix with project + platform
    platform = page.platform or "通用"
    return f"/{project_name}/{platform}/{'/'.join(parts)}"


# ── Coverage Report ──

def get_sync_coverage(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
) -> dict:
    """Get Wiki sync coverage stats for a release bundle.

    Returns dict with:
      - total_pages: total module pages in bundle
      - synced_pages: pages with active Wiki raw sources
      - stale_pages: pages with superseded raw sources (needs re-sync)
      - missing_pages: pages with no Wiki entry
    """
    pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type.in_(["page", "attachment"]),
            )
        ).all()
    )

    total = len(pages)
    synced = 0
    stale = 0
    missing = 0

    for page in pages:
        immutable_version = f"bundle:{release_bundle_id}:module:{page.id}"
        raw_source = db.scalar(
            select(WikiRawSource).where(
                WikiRawSource.project_id == project_id,
                WikiRawSource.immutable_version == immutable_version,
            ).order_by(WikiRawSource.id.desc())
        )

        if not raw_source:
            missing += 1
        elif raw_source.status == "active":
            synced += 1
        elif raw_source.status == "superseded":
            stale += 1
        else:
            missing += 1

    return {
        "total_pages": total,
        "synced_pages": synced,
        "stale_pages": stale,
        "missing_pages": missing,
        "coverage_rate": round(synced / max(1, total), 3),
    }


# ── Diff: Module Tree vs Wiki ──

def diff_module_tree_vs_wiki(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    project_name: str = _PROJECT_NAME,
) -> dict:
    """Compare module tree structure against existing Wiki pages.

    Returns differences: pages in tree but not wiki, pages in wiki but not tree,
    and pages whose content has changed.
    """
    pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type.in_(["page", "attachment"]),
            )
        ).all()
    )

    all_modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
            )
        ).all()
    )
    module_by_id = {m.id: m for m in all_modules}

    tree_paths: dict[str, int] = {}  # wiki_path → module_id
    for page in pages:
        wiki_path = _resolve_path(page, module_by_id, project_name)
        tree_paths[wiki_path] = page.id

    # Load existing WikiRawSources for this bundle
    existing_raw = list(
        db.scalars(
            select(WikiRawSource).where(
                WikiRawSource.project_id == project_id,
                WikiRawSource.business_ref_type == "requirement_module",
                WikiRawSource.status == "active",
            )
        ).all()
    )

    wiki_paths: set[str] = {rs.source_ref for rs in existing_raw if rs.source_ref}

    only_in_tree = set(tree_paths.keys()) - wiki_paths
    only_in_wiki = wiki_paths - set(tree_paths.keys())
    in_both = set(tree_paths.keys()) & wiki_paths

    return {
        "only_in_tree": sorted(only_in_tree),
        "only_in_wiki": sorted(only_in_wiki),
        "in_both": len(in_both),
        "total_tree_pages": len(tree_paths),
        "total_wiki_pages": len(wiki_paths),
    }
