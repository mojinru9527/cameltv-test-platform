"""Requirement service — orchestrate upload → parse → AI-generate → import pipeline."""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.requirement import RequirementDocument
from app.models.requirement_review import RequirementReview
from app.models.test_case import TestCase
from app.models.user import User

logger = logging.getLogger("requirement_service")


def _finish_write(db: Session, row=None, *, commit: bool) -> None:
    """Flush a unit of work, optionally committing for legacy direct callers."""
    if commit:
        db.commit()
    else:
        db.flush()
    if row is not None:
        db.refresh(row)


def _doc_to_dict(r: RequirementDocument, creator_name: str = "") -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "creator_id": r.creator_id,
        "creator_name": creator_name,
        "title": r.title,
        "file_type": r.file_type,
        "source_ref": r.source_ref,
        "source_url": getattr(r, "source_url", ""),
        "content": r.content,
        "ai_raw": r.ai_raw,
        "extraction_raw": r.extraction_raw,
        "status": r.status,
        "extraction_status": getattr(r, "extraction_status", "not_started"),
        "extraction_meta": getattr(r, "extraction_meta", "{}"),
        "imported_count": r.imported_count,
        "imported_func_count": r.imported_func_count,
        "imported_api_count": r.imported_api_count,
        "imported_func_indices": r.imported_func_indices,
        "imported_api_indices": r.imported_api_indices,
        # Version diff fields (batch-26)
        "doc_id": getattr(r, "doc_id", ""),
        "version": getattr(r, "version", ""),
        "parent_id": getattr(r, "parent_id", None),
        "diff_json": getattr(r, "diff_json", ""),
        "diff_status": getattr(r, "diff_status", "initial"),
        "release_bundle_id": getattr(r, "release_bundle_id", None),
        "linked_swagger_id": getattr(r, "linked_swagger_id", None),
        "linked_api_endpoint_ids": sorted(
            _parse_indices(getattr(r, "linked_api_endpoint_ids", "[]"))
        ),
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
    source_url: str = "",
    content: str,
    parsed_type: str = "requirement",
    excel_cases: list[dict] | None = None,
    release_bundle_id: int | None = None,
    commit: bool = True,
) -> dict:
    """Store a parsed requirement document."""
    row = RequirementDocument(
        project_id=project_id,
        creator_id=creator_id,
        title=title,
        file_type=file_type,
        source_ref=source_ref,
        source_url=source_url,
        release_bundle_id=release_bundle_id,
        content=content,
        status="parsed",
    )
    db.add(row)
    _finish_write(db, row, commit=commit)
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


def list_requirements_page(
    db: Session,
    project_id: int,
    *,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, list[tuple[RequirementDocument, str]]]:
    """分页列出项目内需求文档（含创建人用户名），返回 (total, [(doc, creator_name), ...])。

    Batch 181（FIX-173-P2-10）：从路由层收敛的分页查询，路由层据此组装 Page。
    """
    filters = [RequirementDocument.project_id == project_id]
    if keyword:
        filters.append(
            RequirementDocument.title.contains(keyword)
            | RequirementDocument.source_ref.contains(keyword)
        )
    count_stmt = select(func.count()).select_from(RequirementDocument).where(*filters)
    total = db.scalar(count_stmt) or 0
    rows = list(db.execute(
        select(RequirementDocument, User.username)
        .outerjoin(User, User.id == RequirementDocument.creator_id)
        .where(*filters)
        .order_by(RequirementDocument.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all())
    return total, rows


def get_requirement_by_source(db: Session, source_ref: str, project_id: int) -> dict | None:
    """Find a requirement document by its source_ref (URL or filename)."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.source_ref == source_ref,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row:
        return None
    return _doc_to_dict(row)


def update_ai_result(
    db: Session,
    doc_id: int,
    ai_result: dict,
    *,
    commit: bool = True,
) -> dict | None:
    """Save AI generation raw response to the document."""
    row = db.get(RequirementDocument, doc_id)
    if not row:
        return None
    row.ai_raw = json.dumps(ai_result, ensure_ascii=False)
    row.status = "generated"
    _finish_write(db, row, commit=commit)
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


_EDITABLE_CASE_FIELDS = frozenset({
    "title",
    "priority",
    "domain",
    "module",
    "case_design_method",
    "positive_negative",
    "test_data_note",
    "preconditions",
    "steps",
    "expected_result",
    "api_headers",
    "api_body",
    "api_assertions",
    "api_method",
    "api_endpoint",
    "remark",
    "client_scope",
})


def _parse_indices(raw: str) -> set[int]:
    try:
        values = json.loads(raw or "[]")
    except (json.JSONDecodeError, TypeError):
        return set()
    return {value for value in values if isinstance(value, int)}


def _generated_cases(ai_result: dict) -> list[dict]:
    """Return AI cases with canonical global indices and server-owned types."""
    cases: list[dict] = []
    index = 0
    for source in ai_result.get("functional_cases", []):
        case = dict(source)
        case["index"] = index
        case["case_type"] = "manual"
        cases.append(case)
        index += 1
    for source in ai_result.get("api_cases", []):
        case = dict(source)
        case["index"] = index
        case["case_type"] = "api"
        cases.append(case)
        index += 1
    return cases


def replace_review_queue(
    db: Session,
    doc_id: int,
    ai_result: dict,
) -> None:
    """Replace stale review rows when a document is regenerated."""
    db.execute(
        delete(RequirementReview).where(
            RequirementReview.requirement_id == doc_id
        )
    )
    for case in _generated_cases(ai_result):
        db.add(RequirementReview(
            requirement_id=doc_id,
            case_index=case["index"],
            case_type=case["case_type"],
            status="pending",
            edited_data="{}",
            reviewer_id=0,
            reviewed_at=None,
        ))
    db.flush()


def _review_rows(
    db: Session,
    doc_id: int,
) -> dict[tuple[str, int], RequirementReview]:
    rows = db.scalars(
        select(RequirementReview).where(
            RequirementReview.requirement_id == doc_id
        )
    ).all()
    return {(row.case_type, row.case_index): row for row in rows}


def get_review_state(
    db: Session,
    doc_id: int,
    project_id: int,
) -> dict | None:
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
    except (json.JSONDecodeError, TypeError):
        return None

    reviews = _review_rows(db, doc_id)
    imported_func = _parse_indices(row.imported_func_indices)
    imported_api = _parse_indices(row.imported_api_indices)
    functional_cases: list[dict] = []
    api_cases: list[dict] = []
    approved = 0
    rejected = 0

    for case in _generated_cases(ai_result):
        review = reviews.get((case["case_type"], case["index"]))
        status = review.status if review else "pending"
        if status == "approved":
            approved += 1
        elif status == "rejected":
            rejected += 1
        edited_data: dict | None = None
        if review and review.edited_data:
            try:
                parsed = json.loads(review.edited_data)
                edited_data = parsed if parsed else None
            except (json.JSONDecodeError, TypeError):
                edited_data = None
        item = dict(case)
        steps = item.get("steps", "[]")
        if isinstance(steps, (list, dict)):
            item["steps"] = json.dumps(steps, ensure_ascii=False)
        item["review_status"] = status
        item["edited_data"] = edited_data
        if case["case_type"] == "api":
            item["imported"] = case["index"] in imported_api
            api_cases.append(item)
        else:
            item["imported"] = case["index"] in imported_func
            functional_cases.append(item)

    total = len(functional_cases) + len(api_cases)
    return {
        "document_title": row.title,
        "functional_cases": functional_cases,
        "api_cases": api_cases,
        "summary": {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": total - approved - rejected,
        },
    }


def set_review_action(
    db: Session,
    *,
    doc_id: int,
    project_id: int,
    case_index: int,
    action: str,
    reviewer_id: int,
    edited_data: dict | None = None,
    commit: bool = True,
) -> dict | None:
    doc = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not doc or not doc.ai_raw:
        return None
    try:
        cases = _generated_cases(json.loads(doc.ai_raw))
    except (json.JSONDecodeError, TypeError):
        return None
    case = next((item for item in cases if item["index"] == case_index), None)
    if case is None:
        return None

    review = db.scalar(
        select(RequirementReview).where(
            RequirementReview.requirement_id == doc_id,
            RequirementReview.case_type == case["case_type"],
            RequirementReview.case_index == case_index,
        )
    )
    if review is None:
        review = RequirementReview(
            requirement_id=doc_id,
            case_index=case_index,
            case_type=case["case_type"],
            status="pending",
            edited_data="{}",
        )
        db.add(review)

    if action == "edit":
        safe_edits = {
            key: value
            for key, value in (edited_data or {}).items()
            if key in _EDITABLE_CASE_FIELDS
        }
        if not safe_edits:
            from app.core.exceptions import APIException

            raise APIException(
                code=400,
                msg="edited_data 不包含可编辑字段",
                http_status=400,
            )
        review.edited_data = json.dumps(safe_edits, ensure_ascii=False)
        review.status = "edited"
    elif action == "approve":
        review.status = "approved"
    elif action == "reject":
        review.status = "rejected"
    else:
        from app.core.exceptions import APIException

        raise APIException(code=400, msg="不支持的审查动作", http_status=400)

    review.reviewer_id = reviewer_id
    review.reviewed_at = datetime.now()
    _finish_write(db, review, commit=commit)
    try:
        saved_edits = json.loads(review.edited_data or "{}")
    except json.JSONDecodeError:
        saved_edits = {}
    return {
        "index": case_index,
        "case_type": case["case_type"],
        "review_status": review.status,
        "edited_data": saved_edits or None,
    }


def prepare_cases_for_import(
    db: Session,
    *,
    doc_id: int,
    project_id: int,
    indices: list[int],
    edited_cases: list[dict] | None = None,
    reviewer_id: int = 0,
) -> list[dict]:
    """Resolve selected cases and merge persisted/request edits safely."""
    doc = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not doc or not doc.ai_raw:
        return []
    try:
        canonical_cases = _generated_cases(json.loads(doc.ai_raw))
    except (json.JSONDecodeError, TypeError):
        return []

    requested = list(dict.fromkeys(indices))
    case_map = {case["index"]: case for case in canonical_cases}
    missing = [index for index in requested if index not in case_map]
    if missing:
        from app.core.exceptions import APIException

        raise APIException(
            code=400,
            msg=f"用例索引不存在: {missing}",
            http_status=400,
        )

    request_edits: dict[int, dict] = {}
    for edit in edited_cases or []:
        index = edit.get("index")
        if index not in requested:
            from app.core.exceptions import APIException

            raise APIException(
                code=400,
                msg=f"编辑内容未对应已选择用例: {index}",
                http_status=400,
            )
        request_edits[index] = {
            key: value
            for key, value in edit.items()
            if key in _EDITABLE_CASE_FIELDS
        }
        if request_edits[index]:
            set_review_action(
                db,
                doc_id=doc_id,
                project_id=project_id,
                case_index=index,
                action="edit",
                reviewer_id=reviewer_id,
                edited_data=request_edits[index],
                commit=False,
            )

    reviews = _review_rows(db, doc_id)
    selected: list[dict] = []
    for index in requested:
        case = dict(case_map[index])
        review = reviews.get((case["case_type"], index))
        if review and review.edited_data:
            try:
                persisted_edits = json.loads(review.edited_data)
            except (json.JSONDecodeError, TypeError):
                persisted_edits = {}
            case.update({
                key: value
                for key, value in persisted_edits.items()
                if key in _EDITABLE_CASE_FIELDS
            })
        case.update(request_edits.get(index, {}))
        case["index"] = index
        case["case_type"] = case_map[index]["case_type"]
        selected.append(case)
    return selected


def delete_requirement(
    db: Session,
    doc_id: int,
    project_id: int,
    *,
    commit: bool = True,
) -> bool:
    """Delete a requirement document. Returns True if deleted, False if not found."""
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not row:
        return False
    db.execute(
        delete(RequirementReview).where(
            RequirementReview.requirement_id == doc_id
        )
    )
    db.delete(row)
    _finish_write(db, commit=commit)
    return True


def update_extraction(
    db: Session,
    doc_id: int,
    extraction_result: dict,
    *,
    commit: bool = True,
    extraction_meta: dict | None = None,
) -> dict | None:
    """Save Stage 1 AI extraction raw response and set status to pending_review."""
    row = db.get(RequirementDocument, doc_id)
    if not row:
        return None
    row.extraction_raw = json.dumps(extraction_result, ensure_ascii=False)
    if extraction_meta is not None:
        row.extraction_meta = json.dumps(extraction_meta, ensure_ascii=False)
    row.extraction_status = "pending_review"
    _finish_write(db, row, commit=commit)
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


def confirm_extraction(
    db: Session,
    doc_id: int,
    confirmed_data: dict,
    action: str,
    *,
    commit: bool = True,
) -> dict | None:
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
    _finish_write(db, row, commit=commit)
    return _doc_to_dict(row)


def _parent_module_map(doc) -> dict[str, str]:
    """batch-168：由需求提取结果构建「功能点标题/id → 父模块名」映射。

    老数据用例的 module 字段多为功能点级名称（如 MOD-8/FP-3 ...），
    用该映射把用例归属到提取结果中的父模块，保证覆盖矩阵对齐。
    """

    def _norm(text: str) -> str:
        return (text or "").strip().replace(" ", "").lower()

    result: dict[str, str] = {}
    try:
        extraction = json.loads(doc.extraction_raw or "{}")
    except (json.JSONDecodeError, TypeError):
        return result
    for mod in extraction.get("modules") or []:
        mod_name = str(mod.get("name") or "")
        if not mod_name:
            continue
        for fp in mod.get("function_points") or []:
            for key in (fp.get("title"), fp.get("id")):
                if key:
                    result[str(key).strip()] = mod_name
                    result[_norm(str(key))] = mod_name
    return result


def _resolve_fp_parent_module(fp_map: dict[str, str], case_module: str) -> str | None:
    """batch-168：把功能点级 module 字符串（如「开屏广告」「MOD-8/FP-3 ...」）解析到父模块。

    用例生成时的 module 字段是 FP 标题的截断/别名，与提取结果标题不完全相等；
    因此先精确/包含匹配，再用双字块重叠兜底。
    """

    def _norm(text: str) -> str:
        return (text or "").strip().replace(" ", "").lower()

    def _bigrams(text: str) -> set[str]:
        return {text[i:i + 2] for i in range(len(text) - 1)}

    c = _norm(case_module)
    if not c:
        return None
    if c in fp_map:
        return fp_map[c]
    best = None
    best_ratio = 0.0
    cb = _bigrams(c)
    for title, parent in fp_map.items():
        t = _norm(title)
        if not t:
            continue
        if c in t or t in c:
            return parent
        tb = _bigrams(t)
        overlap = len(cb & tb)
        if overlap:
            ratio = max(overlap / len(cb), overlap / len(tb))
            if ratio >= 0.5 and ratio > best_ratio:
                best = parent
                best_ratio = ratio
    return best


def import_cases(
    db: Session,
    doc_id: int,
    cases: list[dict],
    project_id: int,
    *,
    commit: bool = True,
    creator_id: int = 0,
    create_plan: bool = False,
    create_ui_cases: bool = False,
) -> dict:
    """Import selected generated cases into the test_case table (transactional).

    All cases import atomically — if any case fails, the entire batch rolls back
    so no half-imported data is left behind.

    When create_plan=True, also creates a TestPlan and links all imported cases.
    """
    imported_func = 0
    imported_api = 0
    skipped = 0
    requested_func_indices: set[int] = set()
    requested_api_indices: set[int] = set()
    ui_case_ids: list[int] = []
    ui_created = 0

    try:
        row = db.scalar(
            select(RequirementDocument).where(
                RequirementDocument.id == doc_id,
                RequirementDocument.project_id == project_id,
            ).with_for_update()
        )
        if row is None:
            from app.core.exceptions import not_found

            raise not_found("需求文档")

        previous_func = _parse_indices(row.imported_func_indices)
        previous_api = _parse_indices(row.imported_api_indices)
        fp_parent_map = _parent_module_map(row)
        if fp_parent_map:
            from app.models.requirement_module import RequirementModule as _RM
            _parent_names = set(fp_parent_map.values())
            _parent_rows = db.scalars(
                select(_RM).where(_RM.project_id == project_id, _RM.name.in_(_parent_names))
            ).all()
            _parent_module_ids = {m.name: m.id for m in _parent_rows}
        else:
            _parent_module_ids = {}
        seen_in_request: set[tuple[str, int]] = set()
        from app.services import test_case_service  # 懒加载：避免 requirement_service ↔ test_case_service 环依赖（Batch 155 / P2-12）

        for case in cases:
            case_type = "api" if case.get("case_type") == "api" else "manual"
            case_index = case.get("index")
            if not isinstance(case_index, int):
                from app.core.exceptions import APIException

                raise APIException(code=400, msg="用例缺少有效索引", http_status=400)

            existing = previous_api if case_type == "api" else previous_func
            identity = (case_type, case_index)
            if case_index in existing or identity in seen_in_request:
                skipped += 1
                continue
            seen_in_request.add(identity)

            steps_raw = case.get("steps", "[]")
            if isinstance(steps_raw, (list, dict)):
                steps_raw = json.dumps(steps_raw, ensure_ascii=False)
            test_case_service.create_case(
                db,
                {
                    "project_id": project_id,
                    "title": case.get("title", ""),
                    "domain": case.get("domain", ""),
                    "module": case.get("module", ""),
                    "case_type": case_type,
                    "priority": case.get("priority", "P2"),
                    "case_design_method": case.get("case_design_method", ""),
                    "positive_negative": case.get("positive_negative", ""),
                    "test_data_note": case.get("test_data_note", ""),
                    "preconditions": case.get("preconditions", ""),
                    "steps": steps_raw,
                    "expected_result": case.get("expected_result", ""),
                    "api_headers": json.dumps(case.get("api_headers") or {}, ensure_ascii=False),
                    "api_body": case.get("api_body", ""),
                    "api_assertions": case.get("api_assertions", "[]"),
                    "api_method": case.get("api_method", ""),
                    "api_endpoint": case.get("api_endpoint", ""),
                    "source": "ai_generated",
                    "source_doc_id": doc_id,
                    "source_case_index": case_index,
                    "requirement_module_id": _parent_module_ids.get(
                        _resolve_fp_parent_module(fp_parent_map, case.get("module") or "") or ""
                    ),
                },
                commit=False,
            )
            if case_type == "api":
                imported_api += 1
                requested_api_indices.add(case_index)
            else:
                imported_func += 1
                requested_func_indices.add(case_index)

        # batch-167 Phase 3a: 为 P0/P1 有步骤功能用例生成 UI 自动化变体（幂等）
        ui_case_ids: list[int] = []
        ui_created = 0
        if create_ui_cases:
            # batch-168 D4：补生成 UI 变体时覆盖该文档「全部已导入」功能用例
            # （含历史导入），不止本次新导入，保证老版本数据也能三类型关联。
            _all_func_indices = previous_func | requested_func_indices
            for pc in db.scalars(
                select(TestCase).where(
                    TestCase.project_id == project_id,
                    TestCase.source_doc_id == doc_id,
                    TestCase.is_deleted.is_(False),
                    TestCase.source_case_index.in_(_all_func_indices),
                )
            ).all():
                if pc.priority not in ("P0", "P1"):
                    continue
                try:
                    steps = json.loads(pc.steps or "[]")
                except (json.JSONDecodeError, TypeError):
                    steps = []
                if not isinstance(steps, list) or not steps:
                    continue
                ui_title = f"[UI] {pc.title}"[:220]
                parent_module = _resolve_fp_parent_module(fp_parent_map, pc.module or "") or pc.module or ""
                existing_ui = db.scalar(
                    select(TestCase).where(
                        TestCase.project_id == project_id,
                        TestCase.case_type == "ui",
                        TestCase.title == ui_title,
                        TestCase.module == (pc.module or ""),
                        TestCase.is_deleted.is_(False),
                    )
                )
                if existing_ui:
                    ui_case_ids.append(existing_ui.id)
                    continue
                ui_case = TestCase(
                    project_id=project_id,
                    title=ui_title,
                    domain=pc.domain or "用户端",
                    module=parent_module,
                    case_type="ui",
                    priority=pc.priority,
                    tags=json.dumps(["UI自动化", "auto:functional"], ensure_ascii=False),
                    case_design_method=pc.case_design_method or "场景法",
                    positive_negative=pc.positive_negative or "",
                    test_data_note=pc.test_data_note or "",
                    preconditions=pc.preconditions or "",
                    steps=pc.steps or "[]",
                    expected_result=pc.expected_result or "",
                    requirement_module_id=_parent_module_ids.get(parent_module, pc.requirement_module_id),
                    source="ai_generated",
                    source_doc_id=doc_id,
                )
                db.add(ui_case)
                db.flush()
                ui_case_ids.append(ui_case.id)
                ui_created += 1

        all_func = previous_func | requested_func_indices
        all_api = previous_api | requested_api_indices
        row.status = "imported"
        row.imported_func_indices = json.dumps(sorted(all_func), ensure_ascii=False)
        row.imported_api_indices = json.dumps(sorted(all_api), ensure_ascii=False)
        row.imported_func_count = len(all_func)
        row.imported_api_count = len(all_api)
        row.imported_count = len(all_func) + len(all_api)
        _finish_write(db, row, commit=commit)

        # Auto-create test plan if requested
        plan_id = None
        plan_name = ""
        if create_plan and (imported_func > 0 or imported_api > 0 or ui_created > 0):
            from app.services.test_plan_service import add_cases as _add_cases, create_plan as _create_plan
            plan_data = {"name": f"{row.title} - 测试计划", "status": "draft"}
            plan = _create_plan(db, plan_data, creator_id=creator_id, project_id=project_id)
            plan_id = plan["id"]
            plan_name = plan["name"]
            imported_case_ids = [
                tc.id for tc in db.scalars(
                    select(TestCase).where(
                        TestCase.project_id == project_id,
                        TestCase.source_doc_id == doc_id,
                        TestCase.source_case_index.in_(list(requested_func_indices | requested_api_indices)),
                    )
                ).all()
            ]
            imported_case_ids += list(dict.fromkeys(ui_case_ids))
            if imported_case_ids:
                _add_cases(db, plan_id, imported_case_ids, project_id=project_id)
    except Exception as exc:
        db.rollback()
        logger.error(
            "import_cases transaction failed for doc_id=%d: %s\n%s",
            doc_id, exc, traceback.format_exc(),
        )
        raise

    result_payload = {"imported": imported_func + imported_api, "skipped": skipped, "total": len(cases), "plan_id": plan_id, "plan_name": plan_name}
    if ui_created:
        # batch-167: 仅在生成 UI 变体时返回该字段，保持旧契约精确相等
        result_payload["ui_created"] = ui_created
    return result_payload


def get_api_match_selection(
    db: Session,
    *,
    doc_id: int,
    project_id: int,
) -> dict | None:
    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if row is None:
        return None
    return {
        "service_id": row.linked_swagger_id,
        "endpoint_ids": sorted(_parse_indices(row.linked_api_endpoint_ids)),
    }


def confirm_api_match_selection(
    db: Session,
    *,
    doc_id: int,
    project_id: int,
    service_id: int | None,
    endpoint_ids: list[int],
    commit: bool = True,
) -> dict | None:
    """Validate and persist an explicitly confirmed API endpoint selection."""
    from app.core.exceptions import APIException, not_found
    from app.models.api_asset import ApiEndpoint, ApiService

    row = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if row is None:
        return None

    unique_ids = list(dict.fromkeys(endpoint_ids))
    if service_id is None:
        if unique_ids:
            raise APIException(
                code=400,
                msg="选择接口时必须指定 API 服务",
                http_status=400,
            )
    else:
        service = db.scalar(
            select(ApiService).where(
                ApiService.id == service_id,
                ApiService.project_id == project_id,
            )
        )
        if service is None:
            raise not_found("API 服务")

        if unique_ids:
            valid_ids = set(db.scalars(
                select(ApiEndpoint.id).where(
                    ApiEndpoint.id.in_(unique_ids),
                    ApiEndpoint.project_id == project_id,
                    ApiEndpoint.service_id == service_id,
                )
            ).all())
            invalid_ids = [item for item in unique_ids if item not in valid_ids]
            if invalid_ids:
                raise APIException(
                    code=400,
                    msg=f"接口不属于当前项目或所选服务: {invalid_ids}",
                    http_status=400,
                )

    row.linked_swagger_id = service_id
    row.linked_api_endpoint_ids = json.dumps(sorted(unique_ids), ensure_ascii=False)
    _finish_write(db, row, commit=commit)
    return {
        "service_id": row.linked_swagger_id,
        "endpoint_ids": sorted(unique_ids),
    }


# ═══════════════════════════════════════════════════════
# B1: 需求-API 语义映射
# ═══════════════════════════════════════════════════════

_CN_EN_KEYWORDS: dict[str, list[str]] = {
    "首页": ["home"], "热门": ["hot"], "赛事": ["match", "sports"], "比赛": ["match"],
    "联赛": ["competition", "league"], "球队": ["team"], "球员": ["player"], "搜索": ["search"],
    "资讯": ["news"], "回放": ["replay"], "广告": ["ads", "advertisement"], "直播": ["live"],
    "赔率": ["odds"], "下注": ["bet"], "预测": ["forecast", "pick"], "开奖": ["done"],
    "取消": ["cancel"], "充值": ["recharge", "deposit"], "提现": ["withdraw"],
    "付费": ["payment"], "银钻": ["diamond", "silver"], "绿钻": ["diamond", "green"],
    "骆驼币": ["coin"], "任务": ["task"], "配置": ["config"], "后台": ["admin"],
    "登录": ["login"], "注册": ["register"], "账号": ["account"], "账户": ["account"],
    "文章": ["article", "news"], "统计": ["stats", "statistics"], "篮球": ["basketball"],
    "足球": ["football"], "积分": ["score", "points"], "礼物": ["gift"],
    "公告": ["announcement"], "聊天室": ["chat"], "消息": ["message"], "评论": ["comment"],
    "视频": ["video"], "详情": ["detail"], "列表": ["list"], "数据": ["data"],
    "上传": ["upload"], "分析": ["analysis"], "排名": ["rank", "standings"], "赛程": ["schedule"],
    "回放": ["replay"], "公告": ["announcement"],
}


def _expand_keywords(text: str) -> set[str]:
    """把中文需求文本扩展为匹配关键词集合（含中英同义词），用于端点匹配。"""
    lowered = (text or "").lower()
    out = {w for w in lowered.replace("-", " ").replace("_", " ").split() if w}
    for cn, ens in _CN_EN_KEYWORDS.items():
        for en in ens:
            if cn in lowered:
                out.add(en)
                out.add(cn)
            if en in lowered:
                out.add(en)
                out.add(cn)
    return out


def match_api_endpoints(
    db: Session,
    *,
    integration_reqs: list[dict],
    project_id: int,
    service_id: int | None = None,
) -> list[dict]:
    """将 integration 类型的 REQ 功能点匹配到已导入的 ApiEndpoint。

    匹配策略：
    1. 关键词匹配 — 功能点标题/描述中的关键词与 endpoint path/method/summary 匹配
    2. 操作类型匹配 — "列表/查询"→GET, "创建/新增"→POST, "修改/编辑"→PUT, "删除"→DELETE

    Returns: [{req_id, title, endpoint_id, method, path, summary, confidence}]
    """
    from app.models.api_asset import ApiEndpoint

    # 查询项目下所有已导入的 endpoint
    q = db.query(ApiEndpoint).filter(ApiEndpoint.project_id == project_id)
    if service_id:
        q = q.filter(ApiEndpoint.service_id == service_id)
    endpoints = q.all()

    if not endpoints:
        return []

    # 操作关键词 → HTTP method 映射
    method_keywords = {
        "GET": ["列表", "查询", "获取", "搜索", "详情", "list", "get", "query", "search", "read", "fetch"],
        "POST": ["创建", "新增", "添加", "上传", "提交", "create", "add", "upload", "submit", "post"],
        "PUT": ["修改", "编辑", "更新", "变更", "update", "edit", "modify", "put", "patch"],
        "DELETE": ["删除", "移除", "取消", "delete", "remove", "cancel"],
    }

    results: list[dict] = []
    for req in integration_reqs:
        title = (req.get("title") or "").lower()
        desc = (req.get("description") or "").lower()
        combined = f"{title} {desc}"
        synonyms = _expand_keywords(combined)

        best_match = None
        best_score = 0

        for ep in endpoints:
            ep_method = (ep.method or "GET").upper()
            ep_path = (ep.path or "").lower()
            ep_summary = (ep.summary or "").lower()
            ep_module = (ep.module or "").lower()

            score = 0

            # 1. 操作类型匹配
            for method, keywords in method_keywords.items():
                if method == ep_method:
                    for kw in keywords:
                        if kw in combined:
                            score += 3
                            break

            # 2. 路径关键词匹配（含 query/查询 跨 method 的语义命中，batch-167 修正猜路径错配）
            path_segments = [s for s in ep_path.split("/") if s and len(s) > 1]
            for seg in path_segments:
                if seg in combined or any(syn in seg or seg in syn for syn in synonyms if len(syn) >= 2):
                    score += 2
                if ("query" in seg and ("查询" in combined or "query" in combined)) or (
                    "odds" in seg and "赔率" in combined
                ):
                    score += 2

            # 3. 模块关键词匹配（整名命中 + 每字块重叠兜底）
            if ep_module:
                mod_tokens = set(ep_module.replace("-", " ").replace("_", " ").split())
                hits = {t for t in mod_tokens for syn in synonyms if len(syn) >= 2 and (syn in t or t in syn)}
                if hits:
                    score += 3 + min(1, len(hits) - 1)
                elif ep_module in combined:
                    score += 4
                else:
                    overlap = sum(1 for ch in ep_module if ch in combined)
                    if overlap >= max(2, len(ep_module) // 2):
                        score += 2

            # 4. summary 匹配
            summary_words = set(ep_summary.split())
            common = summary_words & synonyms
            score += len(common) * 0.5

            if score > best_score:
                best_score = score
                best_match = {
                    "req_id": req.get("id", ""),
                    "title": req.get("title", ""),
                    "endpoint_id": ep.id,
                    "method": ep.method,
                    "path": ep.path,
                    "summary": ep.summary,
                    "confidence": min(round(best_score / 15, 2), 1.0),
                }

        if best_match and best_match["confidence"] > 0.15:
            results.append(best_match)

    return results







# ── batch-167 Phase 2: integration FP → 已导入真实端点 → 确定性接口用例 ──

def generate_api_cases_from_linked_endpoints(
    db: Session,
    *,
    doc_id: int,
    project_id: int,
    service_id: int | None = None,
    reviewer_id: int = 0,
) -> dict:
    """为需求的 integration 功能点匹配已导入 ApiEndpoint 并确定性生成接口用例。

    batch-168 修正：
    - upsert 不匹配软删除行；模板变体按 (method,path,title) 独立成行。
    - FP 级匹配之外增加模块级匹配：未命中模块用模块名对齐真实端点
      （只读 GET 优先、confidence>=0.4、每模块至多 1 端点、跨模块去重），
      保证接口用例覆盖大多数版本模块。
    """
    from app.models.api_asset import ApiEndpoint, ApiService
    from app.models.requirement_module import RequirementModule
    from app.models.test_case import TestCase
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    doc = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == doc_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if not doc:
        from app.core.exceptions import not_found
        raise not_found("需求文档")

    try:
        extraction = json.loads(doc.extraction_raw or "{}")
    except (json.JSONDecodeError, TypeError):
        extraction = {}
    modules = extraction.get("modules") or []

    integration_reqs: list[dict] = []
    fp_module_by_title: dict[str, str] = {}
    mod_meta: dict[str, dict[str, str]] = {}
    for mod in modules:
        mod_name = str(mod.get("name") or "")
        mod_meta[mod_name] = {
            "description": str(mod.get("description") or ""),
            "id": str(mod.get("id") or mod_name),
        }
        for fp in mod.get("function_points") or []:
            if fp.get("type") == "integration" or fp.get("module") or fp.get("api_endpoint"):
                title = str(fp.get("title") or fp.get("id") or "")
                if title:
                    integration_reqs.append({
                        "id": fp.get("id", title),
                        "title": title,
                        "description": str(fp.get("description") or mod.get("description") or ""),
                    })
                    fp_module_by_title[title] = mod_name

    fp_matches = match_api_endpoints(
        db, integration_reqs=integration_reqs, project_id=project_id, service_id=service_id,
    )
    # 每条匹配带上模块名，供生成时回填 module / requirement_module_id
    matches: list[dict] = []
    for m in fp_matches:
        m2 = dict(m)
        m2["module"] = fp_module_by_title.get(m.get("title", ""), "")
        m2["source"] = "fp"
        matches.append(m2)

    # 模块级兜底匹配（batch-168 D8）
    covered_modules = {m["module"] for m in matches if m.get("module")}
    # 模块级兜底：先为每个未覆盖模块取候选，再按置信度降序逐模块绑定，
    # 允许同一真实端点服务多个相关模块（如广告前端/后台），用 module 维度区分用例行。
    candidates_by_module: dict[str, dict] = {}
    for mod_name, meta in mod_meta.items():
        if not mod_name or mod_name in covered_modules:
            continue
        module_reqs = [{
            "id": meta.get("id", mod_name),
            "title": mod_name,
            "description": meta.get("description", ""),
        }]
        candidates = match_api_endpoints(
            db, integration_reqs=module_reqs, project_id=project_id, service_id=service_id,
        )
        best = None
        for c in candidates:
            if str(c.get("method") or "").upper() not in ("GET", "POST"):
                continue
            if (c.get("confidence") or 0) < 0.4:
                continue
            if best is None or c["confidence"] > best["confidence"]:
                best = c
        if best is not None:
            candidates_by_module[mod_name] = best
    for mod_name in sorted(candidates_by_module, key=lambda name: candidates_by_module[name]["confidence"], reverse=True):
        best = candidates_by_module[mod_name]
        m2 = dict(best)
        m2["module"] = mod_name
        m2["source"] = "module"
        matches.append(m2)
        covered_modules.add(mod_name)

    if not matches:
        return {"matched": 0, "generated": 0, "upserted": 0, "endpoints": [], "message": "没有匹配到已导入的接口端点，请先在接口测试导入 OpenAPI/Swagger"}

    # 模块名 → RequirementModule id（同项目首个同名模块）
    mod_names = {m.get("module") for m in matches if m.get("module")}
    mod_rows = db.scalars(
        select(RequirementModule).where(
            RequirementModule.project_id == project_id,
            RequirementModule.name.in_(mod_names),
        )
    ).all() if mod_names else []
    module_ids = {m.name: m.id for m in mod_rows}

    endpoint_ids = {m["endpoint_id"] for m in matches}
    endpoint_rows = {e.id: e for e in db.scalars(
        select(ApiEndpoint).where(ApiEndpoint.id.in_(endpoint_ids))
    ).all()}
    svc_rows = {s.id: s for s in db.scalars(
        select(ApiService).where(ApiService.id.in_({e.service_id for e in endpoint_rows.values() if e.service_id}))
    ).all()} if endpoint_rows else {}
    service_names = {
        eid: (svc_rows.get(ep.service_id).display_name or svc_rows.get(ep.service_id).name if ep.service_id in svc_rows else "")
        for eid, ep in endpoint_rows.items()
    }

    generated = 0
    upserted = 0
    inserted = 0
    linked_ids = set(_parse_indices(doc.linked_api_endpoint_ids or "[]"))
    seen_identity: set[tuple[str, str, str]] = set()

    def _persist(case: dict, endpoint_dict: dict, module_name: str, source: str = "fp") -> None:
        nonlocal generated, upserted, inserted
        method = case.get("api_method") or endpoint_dict["method"]
        path = case.get("api_endpoint") or endpoint_dict["path"]
        title = str(case.get("title") or f"{method} {path}")
        # batch-168 D3：模板变体按 title 独立成行，避免 method+path 相互覆盖
        module_name_for_key = module_name if source == "module" else ""
        identity = (method, path, title, module_name_for_key)
        if identity in seen_identity:
            return
        seen_identity.add(identity)
        generated += 1
        payload = {
            "project_id": project_id,
            "title": title,
            "domain": "接口测试",
            "module": module_name,
            "case_type": "api",
            "priority": case.get("priority", "P1"),
            "case_design_method": case.get("case_design_method", ""),
            "positive_negative": case.get("positive_negative", ""),
            "test_data_note": case.get("test_data_note", ""),
            "preconditions": case.get("preconditions", ""),
            "steps": json.dumps(case.get("steps", []), ensure_ascii=False),
            "expected_result": case.get("expected_result", ""),
            "api_method": method,
            "api_endpoint": path,
            "api_headers": json.dumps(case.get("api_headers") or {}, ensure_ascii=False),
            "api_body": case.get("api_body", ""),
            "api_assertions": json.dumps(case.get("api_assertions", []), ensure_ascii=False),
            "requirement_module_id": module_ids.get(module_name),
            "source": "ai_generated",
            "source_doc_id": doc_id,
        }
        existing_stmt = select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.case_type == "api",
            TestCase.api_method == method,
            TestCase.api_endpoint == path,
            TestCase.title == title,
            TestCase.is_deleted.is_(False),
        )
        if source == "module":
            existing_stmt = existing_stmt.where(TestCase.module == module_name)
        existing = db.scalar(existing_stmt)
        if existing:
            for key, value in payload.items():
                if key in {"project_id", "case_type"}:
                    continue
                setattr(existing, key, value)
            upserted += 1
        else:
            db.add(TestCase(**payload))
            inserted += 1
            upserted += 1

    for match in matches:
        ep = endpoint_rows.get(match["endpoint_id"])
        if not ep:
            continue
        try:
            request_schema = json.loads(ep.request_schema or "{}")
        except (json.JSONDecodeError, TypeError):
            request_schema = {}
        if not isinstance(request_schema, dict):
            request_schema = {}
        try:
            response_schema = json.loads(ep.response_schema or "{}")
        except (json.JSONDecodeError, TypeError):
            response_schema = {}
        if not isinstance(response_schema, dict):
            response_schema = {}
        endpoint_dict = {
            "service_name": service_names.get(ep.id, ""),
            "module": match.get("module") or ep.module or "",
            "method": ep.method or "GET",
            "path": ep.path or "",
            "summary": ep.summary or "",
            "request_schema": request_schema,
            "response_schema": response_schema,
        }
        module_name = match.get("module") or ep.module or ""
        templates = ["basic", "invalid", "boundary", "security", "smoke"] if match.get("source") == "fp" else ["basic", "positive", "negative"]
        cases = generate_cases_from_endpoint(endpoint_dict, templates=templates)
        for case in cases:
            _persist(case, endpoint_dict, module_name, source=match.get("source", "fp"))
        linked_ids.add(ep.id)

    doc.linked_api_endpoint_ids = json.dumps(sorted(linked_ids), ensure_ascii=False)
    db.commit()
    return {
        "matched": len(matches),
        "generated": generated,
        "upserted": upserted,
        "inserted": inserted,
        "endpoints": [
            {
                "endpoint_id": m["endpoint_id"],
                "method": m["method"],
                "path": m["path"],
                "confidence": m["confidence"],
                "module": m.get("module", ""),
                "source": m.get("source", "fp"),
            }
            for m in matches
        ],
        "message": "",
    }
