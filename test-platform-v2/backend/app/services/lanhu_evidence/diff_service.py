"""Version diff service — compare two lanhu evidence jobs and produce a page-level diff.

Called after a lanhu evidence job completes successfully. Compares the new job's
pages (OCR text + screenshots) against the previous version's pages to determine
what changed (new / modified / unchanged / deleted).

The resulting diff_json is saved to the RequirementDocument for downstream use
(feature extraction scope reduction, knowledge center sync, etc.).
"""
from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage
from app.models.requirement import RequirementDocument

logger = logging.getLogger("lanhu_evidence.diff")

# ── Thresholds ──
TEXT_SIMILARITY_MODIFIED_THRESHOLD = 0.50  # below → new/deleted (no match)
TEXT_SIMILARITY_UNCHANGED_THRESHOLD = 0.90  # above → unchanged


def _parse_version_from_url(url: str) -> str:
    """Extract version string from lanhu URL like .../updates/14.2.0 or ?v=14.2.0"""
    m = None
    if "/updates/" in url:
        m = __import__("re").search(r"/updates/([\d.]+)", url)
    if not m:
        m = __import__("re").search(r"[?&]v(?:ersion)?=([\d.]+)", url)
    return m.group(1) if m else ""


def _parse_doc_id_from_url(url: str) -> str:
    """Extract stable doc_id from lanhu URL (the document identifier portion)."""
    import re
    # Try docId query param first
    m = re.search(r"[?&]docId=(\w+)", url)
    if m:
        return m.group(1)
    # Try path-based doc ID
    m = re.search(r"/document/(\w+)", url)
    if m:
        return m.group(1)
    # Fallback: hash of the path portion
    return ""


def compute_page_diff(
    prev_pages: list[dict[str, Any]],
    curr_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two lists of page dicts (page_name, ocr_text, screenshot_hash) and return diff.

    Matching strategy: try page_name first, then page_path, then order_index as fallback.
    """
    # Build lookup maps
    prev_by_name: dict[str, dict] = {}
    prev_by_path: dict[str, dict] = {}
    for p in prev_pages:
        name = (p.get("page_name") or "").strip()
        path = (p.get("page_path") or "").strip()
        if name:
            prev_by_name[name] = p
        if path:
            prev_by_path[path] = p

    pages: list[dict[str, Any]] = []
    matched_prev: set[int] = set()  # track which prev pages were matched (by index)

    for idx, curr in enumerate(curr_pages):
        curr_name = (curr.get("page_name") or "").strip()
        curr_path = (curr.get("page_path") or "").strip()
        curr_text = (curr.get("ocr_text") or curr.get("merged_text") or "").strip()

        # Try name match, then path match
        prev = prev_by_name.get(curr_name) if curr_name else None
        if prev is None and curr_path:
            prev = prev_by_path.get(curr_path)

        if prev is None:
            # No match → new page
            pages.append({
                "page_index": idx,
                "page_name": curr_name or f"第{idx + 1}页",
                "page_path": curr_path,
                "change_type": "new",
                "text_similarity": 1.0,
                "screenshot_hash": curr.get("screenshot_hash", ""),
                "prev_screenshot_hash": "",
                "ocr_diff": "",
            })
            continue

        # Mark as matched
        prev_idx = prev_pages.index(prev) if prev in prev_pages else -1
        if prev_idx >= 0:
            matched_prev.add(prev_idx)

        prev_text = (prev.get("ocr_text") or prev.get("merged_text") or "").strip()

        # Text similarity
        text_sim = _text_similarity(prev_text, curr_text)

        # Determine change_type
        if text_sim >= TEXT_SIMILARITY_UNCHANGED_THRESHOLD:
            change_type = "unchanged"
        elif text_sim >= TEXT_SIMILARITY_MODIFIED_THRESHOLD:
            change_type = "modified"
        else:
            change_type = "modified"  # low similarity but same name → likely major rework

        # Simple OCR diff snippet
        ocr_diff = ""
        if change_type in ("modified",):
            ocr_diff = _diff_snippet(prev_text, curr_text)

        pages.append({
            "page_index": idx,
            "page_name": curr_name or f"第{idx + 1}页",
            "page_path": curr_path,
            "change_type": change_type,
            "text_similarity": round(text_sim, 3),
            "screenshot_hash": curr.get("screenshot_hash", ""),
            "prev_screenshot_hash": prev.get("screenshot_hash", ""),
            "ocr_diff": ocr_diff[:500],  # truncate
        })

    # Deleted pages (prev pages not matched)
    for idx, prev in enumerate(prev_pages):
        if idx not in matched_prev:
            pages.append({
                "page_index": len(curr_pages) + idx,  # after current pages
                "page_name": (prev.get("page_name") or f"第{idx + 1}页").strip(),
                "page_path": (prev.get("page_path") or "").strip(),
                "change_type": "deleted",
                "text_similarity": 0.0,
                "screenshot_hash": "",
                "prev_screenshot_hash": prev.get("screenshot_hash", ""),
                "ocr_diff": "",
            })

    # Sort: new first, then modified, unchanged, deleted; within type by page_index
    type_order = {"new": 0, "modified": 1, "unchanged": 2, "deleted": 3}
    pages.sort(key=lambda p: (type_order.get(p["change_type"], 9), p["page_index"]))

    summary = {
        "total_pages": len(pages),
        "new_pages": sum(1 for p in pages if p["change_type"] == "new"),
        "modified_pages": sum(1 for p in pages if p["change_type"] == "modified"),
        "unchanged_pages": sum(1 for p in pages if p["change_type"] == "unchanged"),
        "deleted_pages": sum(1 for p in pages if p["change_type"] == "deleted"),
    }

    return {"summary": summary, "pages": pages}


def _text_similarity(a: str, b: str) -> float:
    """Compute similarity between two text strings (0~1)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _diff_snippet(old_text: str, new_text: str) -> str:
    """Generate a short human-readable diff snippet."""
    if not old_text or not new_text:
        return ""
    # Find the first differing block
    matcher = SequenceMatcher(None, old_text, new_text)
    diffs: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            snippet = old_text[i1:i2][:80]
            diffs.append(f"移除: 「{snippet}」")
        elif tag == "insert":
            snippet = new_text[j1:j2][:80]
            diffs.append(f"新增: 「{snippet}」")
        elif tag == "replace":
            old_snippet = old_text[i1:i2][:50]
            new_snippet = new_text[j1:j2][:50]
            diffs.append(f"「{old_snippet}」→「{new_snippet}」")
    return "; ".join(diffs[:5])


def diff_against_previous_version(
    job_id: int,
    project_id: int,
    doc_id: str,
    version: str,
) -> dict[str, Any] | None:
    """Compare this job's pages against the previous version's job pages.

    Returns diff_json dict or None if no previous version exists.
    """
    db = SessionLocal()
    try:
        # Find previous version job (same doc_id, different version, successful)
        prev_job = db.scalar(
            select(LanhuEvidenceJob)
            .where(
                LanhuEvidenceJob.project_id == project_id,
                LanhuEvidenceJob.doc_id == doc_id,
                LanhuEvidenceJob.status.in_(("success", "success_with_warnings")),
                LanhuEvidenceJob.id != job_id,
            )
            .order_by(LanhuEvidenceJob.id.desc())
            .limit(1)
        )

        if prev_job is None:
            logger.info("No previous version found for doc_id=%s — initial version", doc_id)
            return None

        # Fetch pages for both jobs
        curr_pages = list(
            db.scalars(
                select(LanhuEvidencePage)
                .where(LanhuEvidencePage.job_id == job_id)
                .order_by(LanhuEvidencePage.order_index)
            ).all()
        )
        prev_pages = list(
            db.scalars(
                select(LanhuEvidencePage)
                .where(LanhuEvidencePage.job_id == prev_job.id)
                .order_by(LanhuEvidencePage.order_index)
            ).all()
        )

        # Convert to dicts for diff function
        def page_to_dict(p: LanhuEvidencePage) -> dict[str, Any]:
            return {
                "page_name": p.page_name or "",
                "page_path": p.page_path or "",
                "ocr_text": p.ocr_text or "",
                "merged_text": p.merged_text or "",
                "order_index": p.order_index,
                "screenshot_hash": "",
            }

        curr_dicts = [page_to_dict(p) for p in curr_pages]
        prev_dicts = [page_to_dict(p) for p in prev_pages]

        diff = compute_page_diff(prev_dicts, curr_dicts)
        diff["base_version"] = _parse_version_from_url(prev_job.source_url)
        diff["base_job_id"] = prev_job.id
        diff["current_version"] = version
        diff["current_job_id"] = job_id

        logger.info(
            "Diff complete: doc_id=%s, %s→%s, new=%d mod=%d unchanged=%d deleted=%d",
            doc_id,
            diff["base_version"],
            diff["current_version"],
            diff["summary"]["new_pages"],
            diff["summary"]["modified_pages"],
            diff["summary"]["unchanged_pages"],
            diff["summary"]["deleted_pages"],
        )

        return diff

    except Exception:
        logger.exception("Version diff failed for job #%s", job_id)
        return None
    finally:
        db.close()


def sync_diff_to_requirement_document(
    project_id: int,
    doc_id: str,
    version: str,
    diff_json: dict[str, Any] | None,
    source_url: str,
) -> None:
    """Update or create a RequirementDocument with version diff metadata.

    If diff_json is None (initial version), the document gets diff_status="initial".
    If diff_json is provided (update), the document gets diff_status="update" and a
    link to its parent (previous version).
    """
    db = SessionLocal()
    try:
        # Find existing doc by source_ref (URL) or doc_id
        from app.services.requirement_service import get_requirement_by_source
        existing = get_requirement_by_source(db, source_url, project_id)

        if existing is None:
            logger.debug("No existing RequirementDocument for source_url=%s — skip sync", source_url)
            return

        # Find parent (previous version of same doc_id)
        parent_id = None
        if diff_json:
            prev_version = diff_json.get("base_version", "")
            # Look up parent by same doc_id pattern in source_ref, ordered by id desc
            parent = db.scalar(
                select(RequirementDocument)
                .where(
                    RequirementDocument.project_id == project_id,
                    RequirementDocument.source_ref.like(f"%docId={doc_id}%"),
                    RequirementDocument.id != existing["id"],
                )
                .order_by(RequirementDocument.id.desc())
                .limit(1)
            )
            if parent:
                parent_id = parent.id

        # Update metadata on the existing doc
        doc = db.get(RequirementDocument, existing["id"])
        if doc is None:
            return

        diff_status = "update" if diff_json else "initial"
        doc.diff_json = json.dumps(diff_json, ensure_ascii=False) if diff_json else ""
        doc.diff_status = diff_status
        doc.version = version
        doc.doc_id = doc_id
        if parent_id:
            doc.parent_id = parent_id
        db.commit()

        logger.info(
            "Synced diff to RequirementDocument #%s: status=%s, version=%s",
            existing["id"], diff_status, version,
        )

    except Exception:
        logger.exception("Failed to sync diff to RequirementDocument for doc_id=%s", doc_id)
        db.rollback()
    finally:
        db.close()


def run_diff_after_job_completion(
    job_id: int,
    project_id: int,
    source_url: str,
    doc_id: str,
) -> dict[str, Any] | None:
    """Entry point: called after a lanhu evidence job completes successfully.

    1. Parse version from URL
    2. Diff against previous version (if exists)
    3. Sync result to RequirementDocument
    4. Trigger knowledge center sync
    """
    version = _parse_version_from_url(source_url)
    if not version:
        logger.warning("Cannot parse version from URL: %s — skipping diff", source_url)
        return None

    if not doc_id:
        logger.warning("Cannot parse doc_id from URL: %s — skipping diff", source_url)
        return None

    diff = diff_against_previous_version(job_id, project_id, doc_id, version)

    # Sync to RequirementDocument
    sync_diff_to_requirement_document(project_id, doc_id, version, diff, source_url)

    # Sync to knowledge center
    try:
        from app.services.knowledge.ingest_service import ingest_lanhu_version_diff
        ingest_lanhu_version_diff(project_id, doc_id, version, diff, source_url, job_id)
    except Exception:
        logger.exception("Knowledge sync failed for job #%s", job_id)

    return diff
