"""NavigatesToExtractor — 页面交互跳转关系提取器 (v1.2/v1.3)

Four-layer degradation chain for extracting page→page navigation relationships:
  P1 — 蓝湖 HTML DOM 抓取: Parse Axure HTML DOM for clickable elements
  P2 — AI 多模态截图分析: DeepSeek analyzes page screenshots
  P3 — CV 启发式检测 + OCR: OpenCV pattern detection + text matching
  P4 — 手动标注 UI: Manual annotation fallback (handled in frontend)

Output: page_interactions JSON written to RequirementModule.page_interactions.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.lanhu_evidence import LanhuEvidencePage
from app.models.requirement_module import RequirementModule

logger = logging.getLogger("knowledge.navigates_to_extractor")


# ── Dataclasses ──

@dataclass
class PageInteraction:
    """A single interaction from one page to another."""
    trigger: str  # e.g. "点击搜索图标"
    target_page: str  # e.g. "搜索页"
    target_lanhu_page_id: str = ""
    interaction_type: str = "navigation"
    source_element: str = ""
    description: str = ""
    admin_config_source: str = ""  # for dynamic_filter type
    extraction_source: str = ""  # which layer extracted this


@dataclass
class ExtractionReport:
    """Report from an extraction run."""
    total_pages_processed: int = 0
    interactions_found: int = 0
    by_layer: dict[str, int] = field(default_factory=dict)  # layer → count
    by_type: dict[str, int] = field(default_factory=dict)  # interaction_type → count
    pages_with_interactions: int = 0
    pages_without_interactions: int = 0
    failed_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── P3: CV Heuristic Detection ──

# Common UI action verbs in Chinese (from OCR text)
_ACTION_VERBS = [
    "搜索", "提交", "确认", "取消", "返回", "首页", "我的",
    "登录", "注册", "退出", "分享", "收藏", "点赞", "评论",
    "查看", "编辑", "删除", "新增", "添加", "保存", "刷新",
    "筛选", "排序", "下载", "上传", "播放", "暂停",
]

# Common navigation destinations inferred from action verbs
_ACTION_TO_TARGET: dict[str, str] = {
    "搜索": "搜索页",
    "首页": "首页",
    "我的": "个人中心",
    "登录": "登录页",
    "注册": "注册页",
    "评论": "评论页",
    "分享": "分享弹窗",
    "返回": "上一页",
}


def _p3_cv_heuristic(page: RequirementModule, evidence_page: LanhuEvidencePage | None) -> list[PageInteraction]:
    """P3 — CV heuristic: detect common UI patterns from OCR text.

    Uses regex patterns to find action verbs in OCR text and infer targets.
    This is a lightweight fallback when P1 (DOM) and P2 (AI) are unavailable.
    """
    interactions: list[PageInteraction] = []
    ocr_text = evidence_page.merged_text or evidence_page.ocr_text if evidence_page else ""
    if not ocr_text:
        return interactions

    text_lower = ocr_text.lower()

    # Detect action verbs in OCR text
    found_actions: set[str] = set()
    for verb in _ACTION_VERBS:
        if verb in ocr_text:
            found_actions.add(verb)

    # Map detected actions to interactions
    for action in sorted(found_actions):
        target = _ACTION_TO_TARGET.get(action, f"{action}页")
        interactions.append(PageInteraction(
            trigger=f"点击{action}",
            target_page=target,
            interaction_type=_classify_action_type(action),
            source_element=f"OCR检测到'{action}'文字",
            description=f"页面OCR文本中包含'{action}'，推断为可交互元素",
            extraction_source="cv_heuristic",
        ))

    # Detect tab-like patterns: repeated short labels on the same line
    tab_pattern = re.findall(r'(?:首页|推荐|发现|消息|我的|赛事|直播|数据|[^\s]{1,4})\s*', ocr_text)
    if len(tab_pattern) >= 3:
        for tab in tab_pattern[:6]:
            tab = tab.strip()
            if tab and tab not in found_actions:
                interactions.append(PageInteraction(
                    trigger=f"点击Tab-{tab}",
                    target_page=f"{tab}页",
                    interaction_type="tab_switch",
                    source_element=f"底部/顶部Tab栏",
                    description=f"OCR检测到'{tab}'出现在Tab模式中",
                    extraction_source="cv_heuristic",
                ))

    return interactions


def _classify_action_type(action: str) -> str:
    """Classify an action verb into an interaction_type."""
    navigation_actions = {"搜索", "首页", "我的", "返回", "查看"}
    modal_actions = {"登录", "注册", "分享", "确认", "取消"}
    if action in navigation_actions:
        return "navigation"
    if action in modal_actions:
        return "modal"
    return "navigation"


# ── P2: AI Multimodal (stub) ──

async def _p2_ai_multimodal(
    page: RequirementModule,
    screenshot_url: str,
) -> list[PageInteraction]:
    """P2 — AI multimodal screenshot analysis via DeepSeek.

    Currently a stub. Full implementation would:
      1. Send screenshot to DeepSeek Vision API
      2. Ask: "Identify clickable elements, buttons, tabs, and navigation items.
         For each, infer the target page name."
      3. Parse structured JSON response into PageInteraction list.
    """
    logger.debug("P2 AI multimodal not implemented for page #%d", page.id)
    return []


# ── P1: DOM Parsing (stub) ──

def _p1_dom_extraction(
    evidence_page: LanhuEvidencePage | None,
) -> list[PageInteraction]:
    """P1 — Parse Axure HTML DOM for clickable elements.

    Lanhu prototypes are Axure HTML exports. Clickable elements have:
      - <a> tags with href targets
      - data-click / data-link custom attributes
      - Axure hotspot component markers

    Currently a stub — requires lanhu-mcp to fetch the actual HTML DOM.
    """
    if not evidence_page or not evidence_page.dom_text:
        return []

    dom = evidence_page.dom_text
    interactions: list[PageInteraction] = []

    # Try to extract links from DOM text (simple regex as stub)
    link_pattern = re.findall(r'<a[^>]*>(.*?)</a>', dom, re.IGNORECASE)
    for i, link_text in enumerate(link_pattern[:20]):
        text = re.sub(r'<[^>]+>', '', link_text).strip()
        if text:
            interactions.append(PageInteraction(
                trigger=f"点击{text}",
                target_page=f"{text}页",
                interaction_type="navigation",
                source_element=text,
                description=f"DOM <a> 标签: {text}",
                extraction_source="dom",
            ))

    return interactions


# ── Main Extractor ──

async def extract_page_interactions(
    db: Session,
    *,
    page_module_id: int,
    evidence_page_id: int | None = None,
    preferred_layers: list[str] | None = None,
) -> tuple[list[PageInteraction], ExtractionReport]:
    """Extract page interactions for a single page using the degradation chain.

    Args:
        page_module_id: RequirementModule.id for a node_type="page"
        evidence_page_id: Optional LanhuEvidencePage.id for OCR/DOM data
        preferred_layers: Override layer order, e.g. ["dom", "ai", "cv"]

    Returns:
        (interactions, report)
    """
    report = ExtractionReport()
    page = db.get(RequirementModule, page_module_id)
    if not page:
        report.warnings.append(f"Page module #{page_module_id} not found")
        return [], report

    # Load evidence page
    evidence_page = None
    if evidence_page_id:
        evidence_page = db.get(LanhuEvidencePage, evidence_page_id)

    # Determine layer order
    layers = preferred_layers or ["dom", "ai", "cv"]
    all_interactions: list[PageInteraction] = []

    for layer in layers:
        layer_interactions: list[PageInteraction] = []

        if layer == "dom":
            layer_interactions = _p1_dom_extraction(evidence_page)
        elif layer == "ai":
            screenshot_url = ""
            if page.screenshot_urls:
                try:
                    urls = json.loads(page.screenshot_urls)
                    screenshot_url = urls[0] if urls else ""
                except (json.JSONDecodeError, IndexError):
                    pass
            layer_interactions = await _p2_ai_multimodal(page, screenshot_url)
        elif layer == "cv":
            layer_interactions = _p3_cv_heuristic(page, evidence_page)

        report.by_layer[layer] = len(layer_interactions)
        all_interactions.extend(layer_interactions)

        # If we got results from this layer, stop degrading
        if layer_interactions:
            logger.info(
                "Page #%d: layer '%s' found %d interactions — stopping degradation",
                page.id, layer, len(layer_interactions),
            )
            break
        else:
            logger.debug("Page #%d: layer '%s' returned 0 interactions — degrading", page.id, layer)

    # Deduplicate by trigger
    seen_triggers: set[str] = set()
    unique: list[PageInteraction] = []
    for interaction in all_interactions:
        key = f"{interaction.trigger}→{interaction.target_page}"
        if key not in seen_triggers:
            seen_triggers.add(key)
            unique.append(interaction)

    # Classify interaction types
    for interaction in unique:
        int_type = interaction.interaction_type
        report.by_type[int_type] = report.by_type.get(int_type, 0) + 1

    report.total_pages_processed = 1
    report.interactions_found = len(unique)
    if unique:
        report.pages_with_interactions = 1
    else:
        report.pages_without_interactions = 1

    return unique, report


async def extract_all_pages(
    db: Session,
    *,
    release_bundle_id: int,
    preferred_layers: list[str] | None = None,
    save: bool = True,
) -> ExtractionReport:
    """Extract page interactions for ALL pages in a release bundle.

    Args:
        save: If True, persist results to page_interactions field.
    """
    report = ExtractionReport()

    pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type == "page",
            )
        ).all()
    )

    report.total_pages_processed = len(pages)

    for page in pages:
        try:
            # Find matching evidence page
            evidence_page = None
            if page.lanhu_page_id:
                evidence_page = db.scalar(
                    select(LanhuEvidencePage).where(
                        LanhuEvidencePage.page_id == page.lanhu_page_id,
                    )
                )

            interactions, page_report = await extract_page_interactions(
                db,
                page_module_id=page.id,
                evidence_page_id=evidence_page.id if evidence_page else None,
                preferred_layers=preferred_layers,
            )

            if interactions:
                report.pages_with_interactions += 1
                report.interactions_found += len(interactions)

                if save:
                    page.page_interactions = json.dumps(
                        [_interaction_to_dict(i) for i in interactions],
                        ensure_ascii=False,
                    )
                    db.flush()
            else:
                report.pages_without_interactions += 1

            # Accumulate layer stats
            for layer, count in page_report.by_layer.items():
                report.by_layer[layer] = report.by_layer.get(layer, 0) + count
            for int_type, count in page_report.by_type.items():
                report.by_type[int_type] = report.by_type.get(int_type, 0) + count

        except Exception:
            logger.exception("Failed to extract interactions for page #%d", page.id)
            report.failed_pages.append(page.id)

    logger.info(
        "Batch extraction complete: %d pages, %d interactions found, %d failed",
        report.total_pages_processed, report.interactions_found, len(report.failed_pages),
    )
    return report


# ── Serialization ──

def _interaction_to_dict(interaction: PageInteraction) -> dict[str, Any]:
    """Convert PageInteraction to JSON-serializable dict."""
    d = {
        "trigger": interaction.trigger,
        "target_page": interaction.target_page,
        "target_lanhu_page_id": interaction.target_lanhu_page_id,
        "interaction_type": interaction.interaction_type,
        "source_element": interaction.source_element,
        "description": interaction.description,
    }
    if interaction.admin_config_source:
        d["admin_config_source"] = interaction.admin_config_source
    return d


def parse_page_interactions(json_str: str) -> list[PageInteraction]:
    """Parse page_interactions JSON string back to PageInteraction list."""
    try:
        raw = json.loads(json_str or "[]")
    except json.JSONDecodeError:
        return []

    interactions: list[PageInteraction] = []
    for item in raw:
        interactions.append(PageInteraction(
            trigger=item.get("trigger", ""),
            target_page=item.get("target_page", ""),
            target_lanhu_page_id=item.get("target_lanhu_page_id", ""),
            interaction_type=item.get("interaction_type", "navigation"),
            source_element=item.get("source_element", ""),
            description=item.get("description", ""),
            admin_config_source=item.get("admin_config_source", ""),
        ))
    return interactions


# ── Manual Interaction Editing ──

def save_manual_interactions(
    db: Session,
    *,
    page_module_id: int,
    interactions: list[dict],
    merge: bool = True,
) -> list[PageInteraction]:
    """Save manually edited interactions to a page.

    Args:
        merge: If True, merge with existing interactions (dedup by trigger).
               If False, replace entirely.
    """
    page = db.get(RequirementModule, page_module_id)
    if not page:
        raise ValueError(f"Page module #{page_module_id} not found")

    existing: list[PageInteraction] = []
    if merge and page.page_interactions:
        existing = parse_page_interactions(page.page_interactions)

    # Convert new interactions
    new_interactions: list[PageInteraction] = []
    for item in interactions:
        new_interactions.append(PageInteraction(
            trigger=item.get("trigger", ""),
            target_page=item.get("target_page", ""),
            target_lanhu_page_id=item.get("target_lanhu_page_id", ""),
            interaction_type=item.get("interaction_type", "navigation"),
            source_element=item.get("source_element", ""),
            description=item.get("description", ""),
            admin_config_source=item.get("admin_config_source", ""),
            extraction_source="manual",
        ))

    # Merge & dedup
    seen = {f"{i.trigger}→{i.target_page}" for i in existing}
    merged = list(existing)
    for ni in new_interactions:
        key = f"{ni.trigger}→{ni.target_page}"
        if key not in seen:
            seen.add(key)
            merged.append(ni)

    page.page_interactions = json.dumps(
        [_interaction_to_dict(i) for i in merged],
        ensure_ascii=False,
    )
    db.flush()

    logger.info("Saved %d interactions to page #%d (merge=%s)", len(merged), page.id, merge)
    return merged
