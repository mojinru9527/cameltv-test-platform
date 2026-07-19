"""测试用例 Service — CRUD + 域树查询。"""
from __future__ import annotations

import json
import re
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase

# ── P1-2/S2b: HTML sanitization (defense-in-depth against stored XSS) ────

# Tags whose inner content is stripped entirely (dangerous active content)
_DANGEROUS_TAGS_RE = re.compile(
    r"<\s*(script|iframe|object|embed|form|input|textarea|select|option"
    r"|link|meta|base|applet|frame|frameset|ilayer|layer|bgsound"
    r"|xml|style)[^>]*/?\s*>.*?</\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
# Self-closing dangerous tags
_SELF_CLOSING_TAGS_RE = re.compile(
    r"<\s*(script|iframe|object|embed|form|input|textarea|select"
    r"|link|meta|base|applet|frame|frameset)[^>]*/?\s*>",
    re.IGNORECASE,
)
# Event handler attributes (onerror, onclick, onload, etc.)
_EVENT_ATTRS_RE = re.compile(
    r"\s+on\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
    re.IGNORECASE,
)
# javascript: URLs in href/src attributes
_JS_URL_RE = re.compile(
    r"""(href|src|action)\s*=\s*["']?\s*javascript\s*:""",
    re.IGNORECASE,
)

_SAFE_FIELDS = frozenset({
    "title", "preconditions", "steps", "expected_result",
    "description", "remark", "tags", "api_endpoint", "review_comment",
})


def _sanitize_html(value: str) -> str:
    """Strip dangerous HTML tags and event handlers, preserving markdown syntax.

    Strategy: remove dangerous tags first (strip their inner content for
    script/iframe, or just the tag for others), then strip event handler
    attributes and javascript: URLs.
    """
    if not value or not isinstance(value, str):
        return value or ""

    # 1. Remove fully wrapped dangerous tags (strip inner content too)
    cleaned = _DANGEROUS_TAGS_RE.sub("", value)
    # 2. Remove self-closing dangerous tags
    cleaned = _SELF_CLOSING_TAGS_RE.sub("", cleaned)
    # 3. Strip event handler attributes
    cleaned = _EVENT_ATTRS_RE.sub("", cleaned)
    # 4. Strip javascript: URLs
    cleaned = _JS_URL_RE.sub(r'\1=""', cleaned)

    return cleaned.strip()


def _sanitize_case_data(data: dict) -> dict:
    """Sanitize user-controlled text fields in create/update payloads."""
    for field in _SAFE_FIELDS:
        if field in data and isinstance(data[field], str):
            data[field] = _sanitize_html(data[field])
    return data


# ── CRUD ──────────────────────────────────────────────

def list_cases(
    db: Session,
    *,
    project_id: int = 0,
    domain: str = "",
    module: str = "",
    case_type: str = "",
    priority: str = "",
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页查询用例列表，支持多条件筛选。"""
    stmt = select(TestCase)
    count_stmt = select(func.count(TestCase.id))

    # 项目隔离 + 逻辑删除过滤
    stmt = stmt.where(TestCase.project_id == project_id, TestCase.is_deleted == False)
    count_stmt = count_stmt.where(TestCase.project_id == project_id, TestCase.is_deleted == False)

    if domain:
        stmt = stmt.where(TestCase.domain == domain)
        count_stmt = count_stmt.where(TestCase.domain == domain)
    if module:
        stmt = stmt.where(TestCase.module == module)
        count_stmt = count_stmt.where(TestCase.module == module)
    if case_type:
        stmt = stmt.where(TestCase.case_type == case_type)
        count_stmt = count_stmt.where(TestCase.case_type == case_type)
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
        count_stmt = count_stmt.where(TestCase.priority == priority)
    if status:
        stmt = stmt.where(TestCase.status == status)
        count_stmt = count_stmt.where(TestCase.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            (TestCase.title.contains(keyword))
            | (TestCase.case_id.contains(keyword))
            | (TestCase.api_endpoint.contains(keyword))
        )
        count_stmt = count_stmt.where(
            (TestCase.title.contains(keyword))
            | (TestCase.case_id.contains(keyword))
            | (TestCase.api_endpoint.contains(keyword))
        )

    total = db.scalar(count_stmt) or 0

    rows = db.scalars(
        stmt.order_by(TestCase.domain, TestCase.module, TestCase.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return [_row_to_dict(r) for r in rows], total


def get_case(db: Session, case_id: int, project_id: int = 0) -> dict | None:
    row = db.scalar(
        select(TestCase).where(TestCase.id == case_id, TestCase.project_id == project_id)
    )
    return _row_to_dict(row) if row else None


def create_case(db: Session, data: dict) -> dict:
    data = _sanitize_case_data(data)
    row = TestCase(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def update_case(db: Session, case_id: int, data: dict, changed_by: int = 0) -> dict | None:
    data = _sanitize_case_data(data)
    row = db.get(TestCase, case_id)
    if not row:
        return None

    # Auto-version: save snapshot before modifying
    changed_fields = [k for k, v in data.items() if v is not None]
    if changed_fields:
        from app.services.version_service import save_version
        save_version(db, case_id, changed_by=changed_by, changed_fields=",".join(sorted(changed_fields)))

    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def delete_case(db: Session, case_id: int, project_id: int = 0) -> bool:
    row = db.scalar(
        select(TestCase).where(TestCase.id == case_id, TestCase.project_id == project_id)
    )
    if not row:
        return False
    row.is_deleted = True
    db.flush()
    db.commit()
    return True


def batch_delete(db: Session, ids: list[int], project_id: int = 0) -> int:
    rows = db.scalars(
        select(TestCase).where(TestCase.id.in_(ids), TestCase.project_id == project_id)
    ).all()
    for r in rows:
        r.is_deleted = True
    db.flush()
    db.commit()
    return len(rows)


# ── 域树 ──────────────────────────────────────────────

def get_domain_tree(db: Session, project_id: int = 0) -> list[dict]:
    """返回 domain→module 两级树结构，附带每模块用例数。排除已删除的用例。"""
    rows = db.scalars(
        select(TestCase)
        .where(TestCase.project_id == project_id, TestCase.is_deleted == False)
        .order_by(TestCase.domain, TestCase.module)
    ).all()

    tree: dict[str, dict[str, int]] = {}
    for r in rows:
        tree.setdefault(r.domain, {})
        tree[r.domain][r.module] = tree[r.domain].get(r.module, 0) + 1

    result = []
    for domain, modules in tree.items():
        total = sum(modules.values())
        mod_list = [{"module": m, "count": c} for m, c in sorted(modules.items())]
        result.append({"domain": domain, "count": total, "modules": mod_list})

    # 排序：用户端 → 运营后台 → 其他
    _domain_order = {"用户端": 0, "运营后台": 1}
    result.sort(key=lambda d: _domain_order.get(d["domain"], 99))
    return result


# ── 统计 ──────────────────────────────────────────────

def get_stats(db: Session, project_id: int = 0) -> dict:
    """用例总数 / 按类型分布。"""
    rows = db.scalars(select(TestCase).where(TestCase.project_id == project_id)).all()
    types: dict[str, int] = {}
    for r in rows:
        types[r.case_type] = types.get(r.case_type, 0) + 1
    return {"total": len(rows), "by_type": types}


# ── helper ────────────────────────────────────────────

def _row_to_dict(r: TestCase) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "case_id": r.case_id,
        "title": r.title,
        "domain": r.domain,
        "module": r.module,
        "case_type": r.case_type,
        "priority": r.priority,
        "status": r.status,
        "tags": r.tags,
        "preconditions": r.preconditions,
        "steps": r.steps,
        "expected_result": r.expected_result,
        "api_method": r.api_method,
        "api_endpoint": r.api_endpoint,
        "api_spec_ref": r.api_spec_ref,
        "api_headers": r.api_headers,
        "api_body": r.api_body,
        "api_assertions": r.api_assertions,
        "source": r.source,
        "source_doc_id": r.source_doc_id,
        "old_id": r.old_id,
        "review_status": r.review_status,
        "review_comment": r.review_comment,
        "reviewer_id": r.reviewer_id,
        "is_deleted": r.is_deleted,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
