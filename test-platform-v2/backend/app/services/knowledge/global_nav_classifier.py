"""GlobalNavClassifier — 全局导航自动分类器 (v1.3)

Analyzes all page_interactions within a ReleaseBundle and classifies interactions
that appear in >80% of pages as "global_navigation". These are promoted from
per-page page_interactions to ReleaseBundle.global_navigation.

Rationale: Bottom tab bars, top navigation bars, and other persistent UI elements
appear on most (but not all) pages. The 80% threshold allows for edge cases like
full-screen video players or modal overlay pages that temporarily hide navigation.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle

logger = logging.getLogger("knowledge.global_nav_classifier")


# ── Constants ──

GLOBAL_NAV_THRESHOLD = 0.80  # >80% page occurrence → global navigation

# Known global navigation patterns (always promoted regardless of threshold)
_KNOWN_GLOBAL_PATTERNS = [
    "底部导航", "底部Tab", "bottom nav", "bottom tab",
    "顶部导航", "顶部导航栏", "top nav",
    "侧边栏", "sidebar", "抽屉导航",
]


# ── Dataclasses ──

@dataclass
class GlobalNavItem:
    """A single global navigation entry."""
    trigger: str
    target_page: str
    interaction_type: str = "global_navigation"
    coverage: float = 1.0  # fraction of pages containing this interaction
    source_element: str = ""
    description: str = ""


@dataclass
class ClassificationResult:
    """Result of a global navigation classification run."""
    bundle_id: int
    total_pages: int = 0
    pages_with_interactions: int = 0
    global_nav_items: list[GlobalNavItem] = field(default_factory=list)
    removed_from_pages: int = 0  # interactions removed from per-page storage
    warnings: list[str] = field(default_factory=list)


# ── Core Logic ──

def classify_global_navigation(
    db: Session,
    *,
    release_bundle_id: int,
    threshold: float = GLOBAL_NAV_THRESHOLD,
    save: bool = True,
) -> ClassificationResult:
    """Classify and promote global navigation items for a release bundle.

    Algorithm:
      1. Load all page-type modules in the bundle.
      2. Collect all page_interactions across pages.
      3. Group by (trigger, target_page) key.
      4. Items appearing on >threshold fraction of pages → global_navigation.
      5. Remove promoted items from individual page_interactions.
      6. Save to ReleaseBundle.global_navigation.

    Args:
        threshold: Minimum page coverage ratio to qualify as global navigation.
                   Default 0.80 (80%).
        save: If True, persist results to DB.
    """
    result = ClassificationResult(bundle_id=release_bundle_id)

    # Load bundle
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if not bundle:
        result.warnings.append(f"Release bundle #{release_bundle_id} not found")
        return result

    # Load all pages
    pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type == "page",
            )
        ).all()
    )

    result.total_pages = len(pages)
    if not pages:
        result.warnings.append("No pages found in bundle")
        return result

    # ── Collect all interactions ──
    # page_index → list of (trigger, target_page, interaction_dict)
    page_interaction_map: dict[int, list[tuple[str, str, dict]]] = {}
    all_keys: Counter = Counter()

    for page in pages:
        interactions = _parse_interactions(page.page_interactions)
        if not interactions:
            continue
        result.pages_with_interactions += 1
        page_items: list[tuple[str, str, dict]] = []
        for item in interactions:
            trigger = item.get("trigger", "")
            target = item.get("target_page", "")
            key = f"{trigger}→{target}"
            all_keys[key] += 1
            page_items.append((trigger, target, item))
        page_interaction_map[page.id] = page_items

    if not all_keys:
        logger.info("Bundle #%d: no interactions found across %d pages", release_bundle_id, len(pages))
        return result

    # ── Determine global navigation items ──
    min_pages_for_global = max(1, int(result.total_pages * threshold))
    # Also add known patterns that appear on at least 50% of pages
    min_pages_known_pattern = max(1, int(result.total_pages * 0.5))

    global_items: list[GlobalNavItem] = []
    global_keys: set[str] = set()

    for key, count in all_keys.items():
        trigger, target = key.split("→", 1)
        coverage = count / result.total_pages

        is_known = any(p in trigger or p in target for p in _KNOWN_GLOBAL_PATTERNS)

        if count >= min_pages_for_global or (is_known and count >= min_pages_known_pattern):
            # Find the best source_element/description from any occurrence
            source_elem = ""
            description = ""
            for page_items in page_interaction_map.values():
                for t, tg, item in page_items:
                    if t == trigger and tg == target:
                        source_elem = item.get("source_element", "")
                        description = item.get("description", "")
                        break
                if source_elem:
                    break

            item = GlobalNavItem(
                trigger=trigger,
                target_page=target,
                interaction_type="global_navigation",
                coverage=round(coverage, 3),
                source_element=source_elem,
                description=description or f"全局导航: {trigger} (覆盖 {coverage:.0%} 页面)",
            )
            global_items.append(item)
            global_keys.add(key)

    result.global_nav_items = global_items

    if not global_items:
        logger.info(
            "Bundle #%d: no interactions met the %.0f%% threshold (max coverage: %.0f%%)",
            release_bundle_id, threshold * 100,
            max(all_keys.values()) / result.total_pages * 100 if all_keys else 0,
        )
        return result

    # ── Remove promoted items from per-page storage ──
    if save:
        removed_count = 0
        for page in pages:
            if page.id not in page_interaction_map:
                continue
            page_items = page_interaction_map[page.id]
            remaining = [
                item for t, tg, item in page_items
                if f"{t}→{tg}" not in global_keys
            ]
            if len(remaining) < len(page_items):
                removed_count += len(page_items) - len(remaining)
                page.page_interactions = json.dumps(remaining, ensure_ascii=False)
                db.flush()

        result.removed_from_pages = removed_count

        # Save to ReleaseBundle
        bundle.global_navigation = json.dumps(
            [_global_nav_to_dict(item) for item in global_items],
            ensure_ascii=False,
        )
        db.flush()

    logger.info(
        "Bundle #%d: classified %d global nav items (removed %d from per-page storage). "
        "Coverage range: %.0f%%–%.0f%%",
        release_bundle_id, len(global_items), result.removed_from_pages,
        min(i.coverage for i in global_items) * 100 if global_items else 0,
        max(i.coverage for i in global_items) * 100 if global_items else 0,
    )

    return result


# ── Helpers ──

def _parse_interactions(json_str: str) -> list[dict]:
    """Parse page_interactions JSON string."""
    try:
        return json.loads(json_str or "[]")
    except json.JSONDecodeError:
        return []


def _global_nav_to_dict(item: GlobalNavItem) -> dict[str, Any]:
    """Convert GlobalNavItem to JSON-serializable dict."""
    return {
        "trigger": item.trigger,
        "target_page": item.target_page,
        "interaction_type": item.interaction_type,
        "coverage": item.coverage,
        "source_element": item.source_element,
        "description": item.description,
    }


def get_global_navigation(
    db: Session,
    *,
    release_bundle_id: int,
) -> list[GlobalNavItem]:
    """Read global navigation items from a ReleaseBundle."""
    bundle = db.get(ReleaseBundle, release_bundle_id)
    if not bundle or not bundle.global_navigation:
        return []

    try:
        raw = json.loads(bundle.global_navigation)
    except json.JSONDecodeError:
        return []

    items: list[GlobalNavItem] = []
    for item in raw:
        items.append(GlobalNavItem(
            trigger=item.get("trigger", ""),
            target_page=item.get("target_page", ""),
            interaction_type=item.get("interaction_type", "global_navigation"),
            coverage=item.get("coverage", 1.0),
            source_element=item.get("source_element", ""),
            description=item.get("description", ""),
        ))
    return items
