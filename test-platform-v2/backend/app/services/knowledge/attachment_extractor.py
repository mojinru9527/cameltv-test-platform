"""AttachmentContentExtractor — 说明附件内容结构化提取器 (v1.3)

Extracts structured content from attachments (.docx/.pdf/.md) linked to modules.

Process:
  1. Identify node_type="attachment" modules in a release bundle.
  2. Download attachment files (URL from lanhu_page_id or screenshot_urls).
  3. Extract text via OCR or native readers.
  4. AI analysis: identify function points, business rules, flow descriptions.
  5. Store results:
     - summary → attachment node description
     - function_points → attachment node metadata_json
     - business_rules → KnowledgeEntity (entity_type="business_rule")

Does NOT create new RequirementModule nodes (avoids node explosion).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
from app.models.lanhu_evidence import LanhuEvidencePage
from app.models.requirement_module import RequirementModule
from app.models.release_bundle import ReleaseBundle

logger = logging.getLogger("knowledge.attachment_extractor")


# ── Dataclasses ──

@dataclass
class BusinessRule:
    """A business rule extracted from an attachment."""
    rule: str  # e.g. "用户等级≥3才能查看付费内容"
    condition: str  # e.g. "user.level >= 3"
    action: str  # e.g. "显示付费内容入口"
    category: str = ""  # validation | display | access | calculation | workflow
    confidence: float = 0.0


@dataclass
class AttachmentFunctionPoint:
    """A function point extracted from an attachment."""
    name: str
    description: str = ""
    category: str = ""  # CRUD | filter | navigation | display | workflow
    priority: str = ""  # P0 | P1 | P2 | P3


@dataclass
class AttachmentContent:
    """Structured content extracted from an attachment."""
    summary: str = ""
    functional_points: list[AttachmentFunctionPoint] = field(default_factory=list)
    business_rules: list[BusinessRule] = field(default_factory=list)
    related_modules: list[str] = field(default_factory=list)  # AI-inferred related module names
    raw_text: str = ""
    extraction_confidence: float = 0.0


@dataclass
class ExtractionResult:
    """Result of attachment extraction for a bundle."""
    total_attachments: int = 0
    processed: int = 0
    failed: int = 0
    business_rules_created: int = 0
    function_points_extracted: int = 0
    errors: list[str] = field(default_factory=list)


# ── Text Extraction ──

def _extract_text_from_evidence(
    db: Session,
    attachment: RequirementModule,
) -> str:
    """Extract raw text from an attachment using available sources.

    Priority:
      1. LanhuEvidencePage.merged_text (best — has both DOM + OCR)
      2. LanhuEvidencePage.ocr_text
      3. Fallback: empty string
    """
    # Try to find matching evidence page via lanhu_page_id
    if attachment.lanhu_page_id:
        evidence_page = db.scalar(
            select(LanhuEvidencePage).where(
                LanhuEvidencePage.page_id == attachment.lanhu_page_id,
            )
        )
        if evidence_page:
            text = evidence_page.merged_text or evidence_page.ocr_text or ""
            if text:
                logger.debug("Got %d chars from evidence page for attachment #%d", len(text), attachment.id)
                return text

    # Try OCR from evidence pages with matching name
    if attachment.name:
        evidence_page = db.scalar(
            select(LanhuEvidencePage).where(
                LanhuEvidencePage.page_name == attachment.name,
            )
        )
        if evidence_page:
            text = evidence_page.merged_text or evidence_page.ocr_text or ""
            if text:
                return text

    return ""


# ── AI Analysis (stub) ──

async def _ai_analyze_attachment(
    raw_text: str,
    attachment_name: str,
) -> AttachmentContent:
    """AI analysis of attachment text via DeepSeek.

    Currently a stub. Full implementation would:
      1. Send raw_text to DeepSeek with structured prompt:
         "Extract from this document:
          - A 1-2 sentence summary
          - List of functional points (name, description, category)
          - List of business rules (rule text, condition, action)
          - Related module names"
      2. Parse structured JSON response.
      3. Return AttachmentContent.
    """
    logger.debug("AI analysis stub for attachment '%s' (%d chars)", attachment_name, len(raw_text))
    return AttachmentContent(
        summary=f"附件 '{attachment_name}' 的内容摘要（AI分析待实现）",
        raw_text=raw_text,
        extraction_confidence=0.0,
    )


# ── Entity Key Helpers ──

def _attachment_entity_key(project_id: int, attachment_name: str, version: str = "") -> str:
    if version:
        return f"attachment:p{project_id}:{version}:{attachment_name}"
    return f"attachment:p{project_id}:{attachment_name}"


def _business_rule_key(project_id: int, rule_text: str) -> str:
    # Use first 80 chars of rule as stable key
    slug = rule_text.strip()[:80].lower()
    return f"business_rule:p{project_id}:{slug}"


# ── Main Extractor ──

async def extract_attachment_content(
    db: Session,
    *,
    attachment_module_id: int,
    project_id: int,
    version: str = "",
) -> AttachmentContent:
    """Extract and structure content from a single attachment module.

    Returns AttachmentContent with summary, function points, and business rules.
    """
    attachment = db.get(RequirementModule, attachment_module_id)
    if not attachment or attachment.node_type != "attachment":
        return AttachmentContent(
            summary="",
            extraction_confidence=0.0,
        )

    # Step 1: Get raw text
    raw_text = _extract_text_from_evidence(db, attachment)
    if not raw_text:
        logger.warning("No text extracted from attachment #%d '%s'", attachment.id, attachment.name)
        return AttachmentContent(
            summary="无法提取附件文本内容（OCR不可用或附件无文字）",
            raw_text="",
            extraction_confidence=0.0,
        )

    # Step 2: AI analysis
    content = await _ai_analyze_attachment(raw_text, attachment.name)

    # Step 3: Persist results
    if content.summary:
        attachment.description = content.summary

    if content.functional_points:
        current_meta = _parse_json(attachment.metadata_json)
        current_meta["functional_points"] = [
            {"name": fp.name, "description": fp.description, "category": fp.category}
            for fp in content.functional_points
        ]
        attachment.metadata_json = json.dumps(current_meta, ensure_ascii=False)

    db.flush()

    # Step 4: Create business_rule entities
    if content.business_rules:
        _persist_business_rules(db, content.business_rules, attachment, project_id, version)

    logger.info(
        "Attachment #%d extracted: %d chars text, %d function points, %d business rules",
        attachment.id, len(raw_text),
        len(content.functional_points),
        len(content.business_rules),
    )

    return content


async def extract_all_attachments(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    version: str = "",
) -> ExtractionResult:
    """Extract content from ALL attachment modules in a release bundle."""
    result = ExtractionResult()

    attachments = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type == "attachment",
            )
        ).all()
    )

    result.total_attachments = len(attachments)
    if not attachments:
        return result

    for att in attachments:
        try:
            content = await extract_attachment_content(
                db,
                attachment_module_id=att.id,
                project_id=project_id,
                version=version,
            )
            result.processed += 1
            result.business_rules_created += len(content.business_rules)
            result.function_points_extracted += len(content.functional_points)
        except Exception as e:
            logger.exception("Failed to extract attachment #%d '%s'", att.id, att.name)
            result.failed += 1
            result.errors.append(f"Attachment #{att.id} '{att.name}': {e}")

    logger.info(
        "Attachment extraction for bundle #%d: %d/%d processed, %d failed",
        release_bundle_id, result.processed, result.total_attachments, result.failed,
    )

    return result


# ── Business Rule Persistence ──

def _persist_business_rules(
    db: Session,
    rules: list[BusinessRule],
    attachment: RequirementModule,
    project_id: int,
    version: str,
) -> list[KnowledgeEntity]:
    """Create KnowledgeEntity nodes for business rules."""
    created: list[KnowledgeEntity] = []
    attachment_key = _attachment_entity_key(project_id, attachment.name, version)

    for rule in rules:
        rule_key = _business_rule_key(project_id, rule.rule)
        existing = db.scalar(
            select(KnowledgeEntity).where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_key == rule_key,
            )
        )
        if existing:
            continue

        entity = KnowledgeEntity(
            project_id=project_id,
            entity_type="business_rule",
            entity_key=rule_key,
            name=rule.rule[:200],
            description=json.dumps({
                "condition": rule.condition,
                "action": rule.action,
                "category": rule.category,
            }, ensure_ascii=False),
            source_id=None,
            confidence=rule.confidence,
            metadata_json=json.dumps({
                "source_attachment": attachment.name,
                "attachment_id": attachment.id,
                "category": rule.category,
            }, ensure_ascii=False),
        )
        db.add(entity)
        db.flush()
        created.append(entity)

        # Link to attachment entity (described_by relation)
        att_entity = db.scalar(
            select(KnowledgeEntity).where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_key == attachment_key,
            )
        )
        if att_entity:
            rel = KnowledgeRelation(
                project_id=project_id,
                from_entity_id=entity.id,
                relation_type="described_by",
                to_entity_id=att_entity.id,
                confidence=rule.confidence,
                metadata_json=json.dumps({"rule": rule.rule[:200]}, ensure_ascii=False),
            )
            db.add(rel)

        # Also link to related modules if specified
        # (handled by caller through related_modules field)

    if created:
        db.flush()
        logger.info("Created %d business_rule entities for attachment #%d", len(created), attachment.id)

    return created


# ── Helpers ──

def _parse_json(text: str) -> dict:
    try:
        return json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
