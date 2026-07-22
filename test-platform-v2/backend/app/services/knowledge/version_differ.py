"""VersionDiffer — 版本差异分析引擎 (v1.1)

Two-phase diff between a release bundle and its parent:
  Phase A — Rule engine (fast path): folder/page name matching
  Phase B — AI assisted (fallback): content similarity via LLM

Output drives incremental module tree construction for v2+ releases.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.lanhu_evidence import LanhuEvidencePage
from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument

logger = logging.getLogger("knowledge.version_differ")


# ── Dataclasses ──

@dataclass
class PageChange:
    """Per-page change within a modified module."""
    page_name: str
    change: str  # new | modified | deleted | unchanged


@dataclass
class ModuleChange:
    """Change record for a single module between two versions."""
    module_name: str
    parent_module_id: int | None = None  # same module in parent version
    change: str = "new"  # new | modified | deleted | unchanged
    new_pages: list[str] = field(default_factory=list)
    modified_pages: list[str] = field(default_factory=list)
    deleted_pages: list[str] = field(default_factory=list)
    unchanged_pages: list[str] = field(default_factory=list)


@dataclass
class VersionDiffResult:
    """Complete version-to-version diff summary."""
    new_modules: list[str] = field(default_factory=list)
    modified_modules: list[ModuleChange] = field(default_factory=list)
    deleted_modules: list[str] = field(default_factory=list)
    unchanged_modules: list[str] = field(default_factory=list)
    diff_confidence: float = 1.0
    total_pages_diff: int = 0
    warnings: list[str] = field(default_factory=list)


# ── Phase A: Rule Engine ──

def _normalize(name: str) -> str:
    """Normalize a module/page name for comparison — strip whitespace + lowercase."""
    return (name or "").strip().lower()


def _page_key(page: LanhuEvidencePage) -> tuple[str, str]:
    """Composite key for matching: (folder, page_name)."""
    return (_normalize(page.folder), _normalize(page.page_name))


def _rule_diff(
    db: Session,
    current_pages: list[LanhuEvidencePage],
    parent_modules: list[RequirementModule],
    parent_bundle_id: int,
) -> VersionDiffResult:
    """Phase A — rule-based diff via folder/page name comparison.

    Strategy:
      1. Group current pages by folder (≈ module).
      2. Group parent modules (node_type="module") by name.
      3. Match folders ↔ parent module names (exact + fuzzy).
      4. Within matched modules, diff page lists.
    """
    result = VersionDiffResult()

    # ── Group current pages by folder ──
    current_by_folder: dict[str, list[LanhuEvidencePage]] = defaultdict(list)
    for page in current_pages:
        current_by_folder[_normalize(page.folder)].append(page)

    # ── Build parent module index ──
    parent_by_name: dict[str, RequirementModule] = {}
    parent_children: dict[int, list[RequirementModule]] = defaultdict(list)
    for m in parent_modules:
        if m.node_type == "module":
            parent_by_name[_normalize(m.name)] = m
        if m.parent_module_id:
            parent_children[m.parent_module_id].append(m)

    # Load parent pages via DB query (pages are child nodes of modules)
    parent_page_map: dict[int, list[RequirementModule]] = defaultdict(list)
    if parent_modules:
        all_parent_pages = list(
            db.scalars(
                select(RequirementModule).where(
                    RequirementModule.release_bundle_id == parent_bundle_id,
                    RequirementModule.node_type == "page",
                )
            ).all()
        )
        for p in all_parent_pages:
            if p.parent_module_id:
                parent_page_map[p.parent_module_id].append(p)

    # ── Match folders to parent modules ──
    matched_parent_ids: set[int] = set()
    matched_folders: set[str] = set()

    for folder_name, pages in current_by_folder.items():
        if not folder_name:
            continue
        parent_mod = parent_by_name.get(folder_name)
        if parent_mod is None:
            # Fuzzy: try substring match
            for pname, pmod in parent_by_name.items():
                if folder_name in pname or pname in folder_name:
                    parent_mod = pmod
                    break

        if parent_mod is not None:
            matched_folders.add(folder_name)
            matched_parent_ids.add(parent_mod.id)

            # Diff pages within this module
            parent_pages = parent_page_map.get(parent_mod.id, [])
            parent_page_names = {_normalize(p.name) for p in parent_pages}
            current_page_names = {_normalize(p.page_name) for p in pages}

            new_pages = sorted(current_page_names - parent_page_names)
            deleted_pages = sorted(parent_page_names - current_page_names)
            common = current_page_names & parent_page_names

            # For common pages, check if content changed (simple heuristic: name match = unchanged)
            # A deeper content comparison would require OCR text comparison (Phase B)
            mc = ModuleChange(
                module_name=parent_mod.name,
                parent_module_id=parent_mod.id,
                change="modified" if (new_pages or deleted_pages) else "unchanged",
                new_pages=new_pages,
                modified_pages=[],  # content-level changes need Phase B
                deleted_pages=deleted_pages,
                unchanged_pages=sorted(common),
            )
            if mc.change == "unchanged":
                result.unchanged_modules.append(parent_mod.name)
            else:
                result.modified_modules.append(mc)
        else:
            # New module — all pages are new
            result.new_modules.append(folder_name)
            result.total_pages_diff += len(pages)

    # ── Detect deleted modules (in parent but not in current) ──
    for pname, pmod in parent_by_name.items():
        if pmod.id not in matched_parent_ids:
            result.deleted_modules.append(pmod.name)

    # ── Update page diff counts ──
    for mc in result.modified_modules:
        result.total_pages_diff += len(mc.new_pages) - len(mc.deleted_pages)

    result.diff_confidence = 0.85  # rule engine baseline confidence
    return result


# ── Phase B: AI Assisted (stub) ──

async def _ai_diff(
    db: Session,
    current_pages: list[LanhuEvidencePage],
    parent_modules: list[RequirementModule],
    rule_result: VersionDiffResult,
) -> VersionDiffResult:
    """Phase B — AI-assisted diff for cases the rule engine can't resolve.

    Scenarios needing AI:
      - Module renamed (e.g. "资讯模块" → "资讯管理")
      - Module split/merged
      - Content-level page changes within same-named pages

    Currently a stub that returns the rule result unchanged.
    Full implementation requires DeepSeek API integration with OCR text comparison.
    """
    # TODO: Integrate DeepSeek for:
    #   1. For unmatched folders → search parent module names via embedding similarity
    #   2. For common pages → compare OCR text to detect content-level modifications
    #   3. Reclassify confidence based on AI agreement
    logger.info(
        "Phase B AI diff not yet implemented — returning rule result (confidence=%.2f)",
        rule_result.diff_confidence,
    )
    return rule_result


# ── Build Incremental Module Tree ──

def _build_module_tree(
    db: Session,
    diff_result: VersionDiffResult,
    parent_modules: list[RequirementModule],
    current_pages: list[LanhuEvidencePage],
    release_bundle_id: int,
    project_id: int,
    source_version: str,
) -> list[RequirementModule]:
    """Build incremental module tree from diff result.

    Rules:
      - new_modules: create full module→page tree, change_type="new"
      - modified_modules: reuse unchanged_pages via parent_module_id,
        create only new_pages + modified_pages, set parent_module_id
      - deleted_modules: create nodes with change_type="deleted"
      - unchanged_modules: DO NOT create any nodes (frontend pulls from parent)
    """
    created: list[RequirementModule] = []
    parent_by_name = {_normalize(m.name): m for m in parent_modules if m.node_type == "module"}

    # Index current pages by folder
    pages_by_folder: dict[str, list[LanhuEvidencePage]] = defaultdict(list)
    for page in current_pages:
        pages_by_folder[_normalize(page.folder)].append(page)

    # 1. New modules
    for module_name in diff_result.new_modules:
        mod = RequirementModule(
            project_id=project_id,
            release_bundle_id=release_bundle_id,
            name=module_name,
            node_type="module",
            change_type="new",
            source_version=source_version,
        )
        db.add(mod)
        db.flush()
        created.append(mod)

        # Create page nodes
        for page in pages_by_folder.get(_normalize(module_name), []):
            page_node = RequirementModule(
                project_id=project_id,
                release_bundle_id=release_bundle_id,
                name=page.page_name,
                node_type="page",
                platform=_infer_platform(page.folder),
                lanhu_page_id=page.page_id,
                change_type="new",
                parent_module_id=mod.id,
                source_version=source_version,
                screenshot_urls=json.dumps(
                    [page.local_url] if page.local_url else [],
                    ensure_ascii=False,
                ),
            )
            db.add(page_node)
            created.append(page_node)

    # 2. Modified modules
    for mc in diff_result.modified_modules:
        parent_mod = parent_by_name.get(_normalize(mc.module_name))
        mod = RequirementModule(
            project_id=project_id,
            release_bundle_id=release_bundle_id,
            name=mc.module_name,
            node_type="module",
            change_type="modified",
            parent_module_id=parent_mod.id if parent_mod else None,
            source_version=source_version,
        )
        db.add(mod)
        db.flush()
        created.append(mod)

        folder_pages = pages_by_folder.get(_normalize(mc.module_name), [])

        # Create nodes for new + modified pages only
        for page in folder_pages:
            pname_norm = _normalize(page.page_name)
            if pname_norm in {_normalize(p) for p in mc.new_pages}:
                change = "new"
            elif pname_norm in {_normalize(p) for p in mc.modified_pages}:
                change = "modified"
            elif pname_norm in {_normalize(p) for p in mc.unchanged_pages}:
                continue  # skip — frontend will pull from parent
            else:
                change = "modified"  # default for modified module

            page_node = RequirementModule(
                project_id=project_id,
                release_bundle_id=release_bundle_id,
                name=page.page_name,
                node_type="page",
                platform=_infer_platform(page.folder),
                lanhu_page_id=page.page_id,
                change_type=change,
                parent_module_id=mod.id,
                source_version=source_version,
                screenshot_urls=json.dumps(
                    [page.local_url] if page.local_url else [],
                    ensure_ascii=False,
                ),
            )
            db.add(page_node)
            created.append(page_node)

        # Create deleted page markers
        for deleted_name in mc.deleted_pages:
            deleted_node = RequirementModule(
                project_id=project_id,
                release_bundle_id=release_bundle_id,
                name=deleted_name,
                node_type="page",
                change_type="deleted",
                parent_module_id=mod.id,
                source_version=source_version,
            )
            db.add(deleted_node)
            created.append(deleted_node)

    # 3. Deleted modules — create markers
    for module_name in diff_result.deleted_modules:
        mod = RequirementModule(
            project_id=project_id,
            release_bundle_id=release_bundle_id,
            name=module_name,
            node_type="module",
            change_type="deleted",
            source_version=source_version,
        )
        db.add(mod)
        created.append(mod)

    # 4. Unchanged modules — explicitly skip (no nodes created)
    logger.info(
        "Skipped %d unchanged modules (frontend inherits from parent bundle #%d)",
        len(diff_result.unchanged_modules),
        parent_modules[0].release_bundle_id if parent_modules else 0,
    )

    return created


# ── Platform Inference ──

def _infer_platform(folder: str) -> str:
    """Infer platform from folder name heuristics."""
    f = _normalize(folder)
    if "app" in f or "客户端" in f or "移动" in f:
        return "APP"
    if "pc" in f or "浏览器" in f or "桌面" in f:
        return "PC"
    if "web" in f or "h5" in f or "移动端" in f:
        return "WEB"
    if "admin" in f or "后台" in f or "运营" in f:
        return "ADMIN"
    return ""


# ── Public API ──

async def diff_bundle(
    db: Session,
    *,
    release_bundle_id: int,
    parent_bundle_id: int,
    project_id: int,
    source_version: str = "",
) -> VersionDiffResult:
    """Run version diff between a release bundle and its parent.

    Returns a VersionDiffResult for human review before confirming.
    """
    # Load parent bundle modules
    parent_modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == parent_bundle_id,
            )
        ).all()
    )

    if not parent_modules:
        logger.warning("Parent bundle #%d has no modules — treating as baseline", parent_bundle_id)
        return VersionDiffResult(
            new_modules=[],
            diff_confidence=1.0,
            warnings=["Parent bundle has no modules; all current content treated as baseline."],
        )

    # Load current pages from evidence
    current_pages = list(
        db.scalars(
            select(LanhuEvidencePage).where(
                LanhuEvidencePage.project_id == project_id,
            )
        ).all()
    )

    # Phase A: rule engine
    result = _rule_diff(db, current_pages, parent_modules, parent_bundle_id)

    # Phase B: AI fallback (async, currently stub)
    if result.diff_confidence < 0.9:
        result = await _ai_diff(db, current_pages, parent_modules, result)

    return result


async def confirm_diff(
    db: Session,
    *,
    release_bundle_id: int,
    parent_bundle_id: int,
    diff_result: VersionDiffResult,
    project_id: int,
    source_version: str,
    overrides: dict | None = None,
) -> list[RequirementModule]:
    """Confirm a diff result and build the incremental module tree.

    Args:
        overrides: user corrections to the diff result, e.g.:
            {"reclassify": {"资讯模块": "modified"}, "skip_modules": ["实验模块"]}
    """
    # Apply overrides
    if overrides:
        diff_result = _apply_overrides(diff_result, overrides)

    # Load parent modules for tree building
    parent_modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == parent_bundle_id,
            )
        ).all()
    )

    # Load current evidence pages
    current_pages = list(
        db.scalars(
            select(LanhuEvidencePage).where(
                LanhuEvidencePage.project_id == project_id,
            )
        ).all()
    )

    created = _build_module_tree(
        db, diff_result, parent_modules, current_pages,
        release_bundle_id, project_id, source_version,
    )

    # Update release bundle diff_summary
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if bundle:
        bundle.diff_summary = json.dumps({
            "new_modules": diff_result.new_modules,
            "modified_modules": [
                {
                    "name": m.module_name,
                    "new_pages": m.new_pages,
                    "modified_pages": m.modified_pages,
                    "deleted_pages": m.deleted_pages,
                    "unchanged_pages": m.unchanged_pages,
                }
                for m in diff_result.modified_modules
            ],
            "deleted_modules": diff_result.deleted_modules,
            "unchanged_modules": diff_result.unchanged_modules,
            "total_pages_diff": diff_result.total_pages_diff,
            "diff_confidence": diff_result.diff_confidence,
        }, ensure_ascii=False)

    logger.info(
        "Diff confirmed for bundle #%d: %d new, %d modified, %d deleted, %d unchanged → %d nodes created",
        release_bundle_id,
        len(diff_result.new_modules),
        len(diff_result.modified_modules),
        len(diff_result.deleted_modules),
        len(diff_result.unchanged_modules),
        len(created),
    )
    return created


def _apply_overrides(result: VersionDiffResult, overrides: dict) -> VersionDiffResult:
    """Apply user corrections to a diff result."""
    reclassify: dict[str, str] = overrides.get("reclassify", {})
    skip_modules: list[str] = overrides.get("skip_modules", [])

    for name, new_change in reclassify.items():
        name_norm = _normalize(name)
        # Remove from current category
        if name in result.new_modules:
            result.new_modules.remove(name)
        result.modified_modules = [m for m in result.modified_modules if _normalize(m.module_name) != name_norm]
        if name in result.deleted_modules:
            result.deleted_modules.remove(name)
        if name in result.unchanged_modules:
            result.unchanged_modules.remove(name)
        # Add to new category
        if new_change == "new":
            result.new_modules.append(name)
        elif new_change == "modified":
            result.modified_modules.append(ModuleChange(module_name=name, change="modified"))
        elif new_change == "deleted":
            result.deleted_modules.append(name)
        elif new_change == "unchanged":
            result.unchanged_modules.append(name)

    for name in skip_modules:
        if name in result.new_modules:
            result.new_modules.remove(name)
        result.modified_modules = [m for m in result.modified_modules if m.module_name != name]

    return result
