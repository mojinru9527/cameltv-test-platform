"""Requirement service — orchestrate upload → parse → AI-generate → import pipeline."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import RequirementDocument
from app.models.user import User
from app.services import test_case_service


def _doc_to_dict(r: RequirementDocument, creator_name: str = "") -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "creator_id": r.creator_id,
        "creator_name": creator_name,
        "title": r.title,
        "file_type": r.file_type,
        "source_ref": r.source_ref,
        "content": r.content,
        "ai_raw": r.ai_raw,
        "status": r.status,
        "extraction_status": getattr(r, "extraction_status", "not_started"),
        "imported_count": r.imported_count,
        "imported_func_count": r.imported_func_count,
        "imported_api_count": r.imported_api_count,
        "imported_func_indices": r.imported_func_indices,
        "imported_api_indices": r.imported_api_indices,
        "parsed_type": "requirement",
        "excel_cases": [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def create_requirement(
    db: Session,
    *,
    project_id: int,
    creator_id: int = 0,
    title: str,
    file_type: str,
    source_ref: str,
    content: str,
    parsed_type: str = "requirement",
    excel_cases: list[dict] | None = None,
) -> dict:
    """Store a parsed requirement document."""
    row = RequirementDocument(
        project_id=project_id,
        creator_id=creator_id,
        title=title,
        file_type=file_type,
        source_ref=source_ref,
        content=content,
        status="parsed",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Look up creator name
    creator_name = ""
    if creator_id:
        user = db.get(User, creator_id)
        if user:
            creator_name = user.username
    result = _doc_to_dict(row, creator_name)
    result["parsed_type"] = parsed_type
    result["excel_cases"] = excel_cases or []
    return result


def list_requirements(db: Session, project_id: int) -> list[dict]:
    """List all requirement documents for a project, with creator usernames."""
    rows = db.execute(
        select(RequirementDocument)
        .where(RequirementDocument.project_id == project_id)
        .order_by(RequirementDocument.id.desc())
    ).scalars().all()
    # Collect creator_ids and batch-fetch usernames
    creator_ids = {r.creator_id for r in rows if r.creator_id}
    user_map: dict[int, str] = {}
    if creator_ids:
        users = db.execute(
            select(User.id, User.username).where(User.id.in_(creator_ids))
        ).all()
        user_map = {u.id: u.username for u in users}
    return [_doc_to_dict(r, user_map.get(r.creator_id, "")) for r in rows]


def get_requirement(db: Session, doc_id: int, project_id: int) -> dict | None:
    """Get a single requirement document."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row:
        return None
    creator_name = ""
    if row.creator_id:
        user = db.get(User, row.creator_id)
        if user:
            creator_name = user.username
    return _doc_to_dict(row, creator_name)


def update_ai_result(db: Session, doc_id: int, ai_result: dict) -> dict | None:
    """Save AI generation raw response to the document."""
    row = db.get(RequirementDocument, doc_id)
    if not row:
        return None
    row.ai_raw = json.dumps(ai_result, ensure_ascii=False)
    row.status = "generated"
    db.commit()
    db.refresh(row)
    return _doc_to_dict(row)


def get_requirement_cases(db: Session, doc_id: int, project_id: int) -> dict | None:
    """Return parsed AI-generated cases for a document that has been generated."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row or not row.ai_raw:
        return None
    try:
        ai_result = json.loads(row.ai_raw)
    except json.JSONDecodeError:
        return None

    # Parse previously imported indices
    try:
        imported_func_set = set(json.loads(row.imported_func_indices or "[]"))
    except json.JSONDecodeError:
        imported_func_set: set[int] = set()
    try:
        imported_api_set = set(json.loads(row.imported_api_indices or "[]"))
    except json.JSONDecodeError:
        imported_api_set: set[int] = set()

    # Build structured result with indices (same format as generate endpoint)
    func_cases: list[dict] = []
    api_cases: list[dict] = []
    idx = 0
    for c in ai_result.get("functional_cases", []):
        c["index"] = idx
        c["case_type"] = "manual"
        c["imported"] = idx in imported_func_set
        if isinstance(c.get("steps"), (list, dict)):
            c["steps"] = json.dumps(c["steps"], ensure_ascii=False)
        func_cases.append(c)
        idx += 1
    for c in ai_result.get("api_cases", []):
        c["index"] = idx
        c["case_type"] = "api"
        c["imported"] = idx in imported_api_set
        if isinstance(c.get("steps"), (list, dict)):
            c["steps"] = json.dumps(c["steps"], ensure_ascii=False)
        api_cases.append(c)
        idx += 1
    # Extract requirement_analysis from stored AI result
    analysis_data = ai_result.get("requirement_analysis", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}
    analysis_data.setdefault("extracted_requirements", [])
    analysis_data.setdefault("overall_assessment", "")

    return {
        "document_id": doc_id,
        "requirement_analysis": analysis_data,
        "functional_cases": func_cases,
        "api_cases": api_cases,
        "raw_response": row.ai_raw,
    }


def delete_requirement(db: Session, doc_id: int, project_id: int) -> bool:
    """Delete a requirement document. Returns True if deleted, False if not found."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def update_extraction(db: Session, doc_id: int, extraction_result: dict) -> dict | None:
    """Save Stage 1 AI extraction raw response and set status to pending_review."""
    row = db.get(RequirementDocument, doc_id)
    if not row:
        return None
    row.extraction_raw = json.dumps(extraction_result, ensure_ascii=False)
    row.extraction_status = "pending_review"
    db.commit()
    db.refresh(row)
    return _doc_to_dict(row)


def get_extraction(db: Session, doc_id: int, project_id: int) -> dict | None:
    """Return parsed Stage 1 extraction result for review."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row or not row.extraction_raw:
        return None
    try:
        extraction_data = json.loads(row.extraction_raw)
    except json.JSONDecodeError:
        return None
    # Build version_info and client_summary from stored data
    changelog = extraction_data.get("changelog", {})
    version_info: list[dict] = []
    client_scope = extraction_data.get("client_scope", [])
    client_summary = f"涉及 {'/'.join(client_scope)}" if client_scope else ""

    if changelog and isinstance(changelog, dict):
        versions = changelog.get("versions", [])
        for v in versions if isinstance(versions, list) else []:
            version_info.append({
                "version": v.get("version", ""),
                "title": v.get("title", ""),
                "update_items": v.get("update_items", []),
                "clients": v.get("clients", []),
                "folder_hint": v.get("folder_hint", ""),
            })

    return {
        "document_id": doc_id,
        "modules": extraction_data.get("modules", []),
        "overall_assessment": extraction_data.get("overall_assessment", ""),
        "raw_response": row.extraction_raw,
        "extraction_status": row.extraction_status,
        "extraction_summary": extraction_data.get("extraction_summary", ""),
        "version_info": version_info,
        "client_summary": client_summary,
    }


def confirm_extraction(db: Session, doc_id: int, confirmed_data: dict, action: str) -> dict | None:
    """Confirm or reject the Stage 1 extraction result.

    action == "confirm": Save confirmed/edited modules, set status to confirmed.
    action == "reject": Reset status to not_started so user can re-extract.
    """
    row = db.get(RequirementDocument, doc_id)
    if not row:
        return None
    if action == "confirm":
        # Store the confirmed version (may include user edits to modules)
        row.extraction_raw = json.dumps(confirmed_data, ensure_ascii=False)
        row.extraction_status = "confirmed"
    elif action == "reject":
        # Reset to allow re-extraction
        row.extraction_status = "not_started"
    else:
        return None
    db.commit()
    db.refresh(row)
    return _doc_to_dict(row)


def import_cases(
    db: Session,
    doc_id: int,
    cases: list[dict],
    project_id: int,
) -> dict:
    """Import selected generated cases into the test_case table (transactional).

    All cases import atomically — if any case fails, the entire batch rolls back
    so no half-imported data is left behind.
    """
    from app.core.base_service import transaction

    imported_func = 0
    imported_api = 0
    skipped = 0
    func_indices: list[int] = []
    api_indices: list[int] = []

    try:
        with transaction(db):
            for c in cases:
                case_type = c.get("case_type", "manual")
                case_index = c.get("index")
                try:
                    steps_raw = c.get("steps", "[]")
                    if isinstance(steps_raw, list):
                        steps_raw = json.dumps(steps_raw, ensure_ascii=False)
                    test_case_service.create_case(db, {
                        "project_id": project_id,
                        "title": c.get("title", ""),
                        "domain": c.get("domain", ""),
                        "module": c.get("module", ""),
                        "case_type": case_type,
                        "priority": c.get("priority", "P2"),
                        "preconditions": c.get("preconditions", ""),
                        "steps": steps_raw,
                        "expected_result": c.get("expected_result", ""),
                        "api_method": c.get("api_method", ""),
                        "api_endpoint": c.get("api_endpoint", ""),
                        "source": "ai_generated",
                        "source_doc_id": doc_id,
                    })
                    if case_type == "api":
                        imported_api += 1
                        if case_index is not None:
                            api_indices.append(case_index)
                    else:
                        imported_func += 1
                        if case_index is not None:
                            func_indices.append(case_index)
                except Exception:
                    skipped += 1

            # Update document status with per-type tracking
            row = db.get(RequirementDocument, doc_id)
            if row:
                row.status = "imported"
                row.imported_count = imported_func + imported_api

                try:
                    prev_func = json.loads(row.imported_func_indices or "[]")
                except json.JSONDecodeError:
                    prev_func = []
                try:
                    prev_api = json.loads(row.imported_api_indices or "[]")
                except json.JSONDecodeError:
                    prev_api = []

                new_func = list(set(prev_func + func_indices))
                new_api = list(set(prev_api + api_indices))

                row.imported_func_indices = json.dumps(new_func, ensure_ascii=False)
                row.imported_api_indices = json.dumps(new_api, ensure_ascii=False)
                row.imported_func_count = len(new_func)
                row.imported_api_count = len(new_api)
    except Exception:
        imported_func = 0
        imported_api = 0
        skipped = len(cases)

    return {"imported": imported_func + imported_api, "skipped": skipped, "total": len(cases)}
