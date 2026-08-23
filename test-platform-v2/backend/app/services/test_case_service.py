"""测试用例 Service — CRUD + 域树查询 + 分类管理。"""
from __future__ import annotations

import re
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_case_category import TestCaseDomain, TestCaseModule
from app.core.execution_status import canonical_exec_status
from app.services.test_case_taxonomy import (
    canonical_case_location,
    classify_case_surface,
    taxonomy_location_matches,
)

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

CASE_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "manual": ("manual", "functional"),
    "api": ("api",),
    "ui": ("ui",),
}

SURFACE_ORDER = {"用户端": 0, "运营后台": 1, "接口测试": 2, "其他": 3}


def canonical_case_type(value: str) -> str:
    """Map legacy persisted values to the product's canonical case types."""
    return "manual" if value == "functional" else value


def case_type_values(value: str) -> tuple[str, ...]:
    """Return persisted values accepted by a canonical type filter."""
    return CASE_TYPE_ALIASES.get(canonical_case_type(value), (value,))


def _module_segments(module: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"[/\\>＞]+", module) if segment.strip()] or ["未分类"]


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
    if isinstance(data.get("case_type"), str):
        data["case_type"] = canonical_case_type(data["case_type"])
    return data


def validate_source_doc(db, source_doc_id: int | None, project_id: int) -> str | None:
    """C68-2：校验用例来源需求文档属于当前项目。返回错误信息或 None。"""
    if source_doc_id is None:
        return None
    from app.services import requirement_service

    doc = requirement_service.get_requirement(db, source_doc_id, project_id=project_id)
    if not doc:
        return "来源需求文档不存在或无权关联"
    return None


# ── CRUD ──────────────────────────────────────────────

def list_cases(
    db: Session,
    *,
    project_id: int = 0,
    case_id: str = "",
    domain: str = "",
    module: str = "",
    surface: str = "",
    taxonomy_domain: str = "",
    taxonomy_module: str = "",
    taxonomy_direct: bool = False,
    case_type: str = "",
    positive_negative: str = "",
    priority: str = "",
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页查询用例列表，支持多条件筛选。"""
    stmt = select(TestCase).where(TestCase.is_deleted.is_(False))
    count_stmt = select(func.count(TestCase.id)).where(TestCase.is_deleted.is_(False))

    # 项目隔离
    stmt = stmt.where(TestCase.project_id == project_id)
    count_stmt = count_stmt.where(TestCase.project_id == project_id)

    if case_id:
        stmt = stmt.where(TestCase.case_id == case_id)
        count_stmt = count_stmt.where(TestCase.case_id == case_id)
    if domain:
        stmt = stmt.where(TestCase.domain == domain)
        count_stmt = count_stmt.where(TestCase.domain == domain)
    if module:
        stmt = stmt.where(TestCase.module == module)
        count_stmt = count_stmt.where(TestCase.module == module)
    if case_type:
        values = case_type_values(case_type)
        stmt = stmt.where(TestCase.case_type.in_(values))
        count_stmt = count_stmt.where(TestCase.case_type.in_(values))
    if positive_negative:
        stmt = stmt.where(TestCase.positive_negative == positive_negative)
        count_stmt = count_stmt.where(TestCase.positive_negative == positive_negative)
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
        count_stmt = count_stmt.where(TestCase.priority == priority)
    if status:
        stmt = stmt.where(TestCase.status == status)
        count_stmt = count_stmt.where(TestCase.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            (TestCase.title.ilike(like))
            | (TestCase.case_id.ilike(like))
            | (TestCase.api_endpoint.ilike(like))
            | (TestCase.domain.ilike(like))
            | (TestCase.module.ilike(like))
            | (TestCase.preconditions.ilike(like))
            | (TestCase.steps.ilike(like))
            | (TestCase.expected_result.ilike(like))
        )
        count_stmt = count_stmt.where(
            (TestCase.title.ilike(like))
            | (TestCase.case_id.ilike(like))
            | (TestCase.api_endpoint.ilike(like))
            | (TestCase.domain.ilike(like))
            | (TestCase.module.ilike(like))
            | (TestCase.preconditions.ilike(like))
            | (TestCase.steps.ilike(like))
            | (TestCase.expected_result.ilike(like))
        )

    if surface or taxonomy_domain or taxonomy_module or taxonomy_direct:
        candidates = db.execute(
            stmt.with_only_columns(
                TestCase.id,
                TestCase.domain,
                TestCase.module,
                TestCase.case_type,
            ).order_by(None)
        ).all()
        matching_ids = [
            row.id
            for row in candidates
            if taxonomy_location_matches(
                canonical_case_location(row.domain, row.module, row.case_type),
                surface=surface,
                domain=taxonomy_domain,
                module_path=taxonomy_module,
                direct_only=taxonomy_direct,
            )
        ]
        if not matching_ids:
            return [], 0
        stmt = stmt.where(TestCase.id.in_(matching_ids))
        count_stmt = count_stmt.where(TestCase.id.in_(matching_ids))

    total = db.scalar(count_stmt) or 0

    rows = db.scalars(
        stmt.order_by(TestCase.domain, TestCase.module, TestCase.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return [_row_to_dict(r) for r in rows], total


def get_case(db: Session, case_id: int, project_id: int = 0) -> dict | None:
    row = db.scalar(
        select(TestCase).where(
            TestCase.id == case_id,
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
    )
    return _row_to_dict(row) if row else None


def create_case(db: Session, data: dict, *, commit: bool = True) -> dict:
    data = _sanitize_case_data(data)
    row = TestCase(**data)
    db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(row)
    return _row_to_dict(row)


def update_case(db: Session, case_id: int, data: dict, changed_by: int = 0) -> dict | None:
    data = _sanitize_case_data(data)
    row = db.scalar(
        select(TestCase).where(TestCase.id == case_id, TestCase.is_deleted.is_(False))
    )
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
        select(TestCase).where(
            TestCase.id == case_id,
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
    )
    if not row:
        return False
    row.is_deleted = True
    return True


def batch_delete(db: Session, ids: list[int], project_id: int = 0) -> int:
    rows = db.scalars(
        select(TestCase).where(
            TestCase.id.in_(ids),
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
    ).all()
    for r in rows:
        r.is_deleted = True
    db.commit()
    return len(rows)


def save_execution_backfill(
    db: Session, case_id: int, project_id: int, result: dict
) -> bool:
    """API 执行结果回填到用例（last_response_json / last_run_status）。

    Batch 181（FIX-173-P2-10）：路由层禁 ORM，原 execute 端点内的 TestCase 查询
    收敛至此；不负责 commit（路由层保留 db.commit()/db.rollback() 的 try/except）。
    """
    import json as _json

    row = db.scalar(
        select(TestCase).where(
            TestCase.id == case_id,
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
    )
    if not row:
        return False
    row.last_response_json = _json.dumps(
        {
            "status_code": result.get("status_code"),
            "response_body": result.get("response_body"),
            "assertions": result.get("assertions", []),
            "assertion_summary": result.get("assertion_summary", {}),
            "all_pass": result.get("all_pass"),
            "executed_at": result.get("executed_at"),
        },
        ensure_ascii=False,
    )
    row.last_run_status = canonical_exec_status("passed" if result.get("all_pass") else "failed")
    return True


# ── 域树 ──────────────────────────────────────────────

def get_domain_tree(db: Session, project_id: int = 0) -> list[dict]:
    """返回 domain→module 两级树结构，附带每模块用例数。过滤已删除用例。"""
    rows = db.scalars(
        select(TestCase)
        .where(TestCase.project_id == project_id, TestCase.is_deleted.is_(False))
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

    # 排序：用户端 → 运营后台 → 接口测试 → 其他
    _domain_order = {"用户端": 0, "运营后台": 1, "接口测试": 2}
    result.sort(key=lambda d: _domain_order.get(d["domain"], 99))
    return result


# ── 统计 ──────────────────────────────────────────────

def get_stats(db: Session, project_id: int = 0) -> dict:
    """用例总数 / 按类型分布。过滤已删除用例。"""
    rows = db.execute(
        select(TestCase.case_type, func.count(TestCase.id))
        .where(TestCase.project_id == project_id, TestCase.is_deleted.is_(False))
        .group_by(TestCase.case_type)
    ).all()
    types: dict[str, int] = {}
    for raw_type, count in rows:
        case_type = canonical_case_type(raw_type)
        types[case_type] = types.get(case_type, 0) + count
    return {"total": sum(types.values()), "by_type": types}


def get_taxonomy(
    db: Session,
    *,
    project_id: int = 0,
    case_type: str = "manual",
    surface: str = "",
) -> list[dict]:
    """构建 界面→业务域→多级模块 的用例分类树。"""
    stmt = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.is_deleted.is_(False),
    )
    if case_type and case_type != "all":
        stmt = stmt.where(TestCase.case_type.in_(case_type_values(case_type)))
    rows = db.scalars(stmt.order_by(TestCase.domain, TestCase.module, TestCase.id)).all()

    grouped: dict[str, dict[str, dict]] = {}
    for row in rows:
        location = canonical_case_location(row.domain, row.module, row.case_type)
        if surface and location.surface != surface:
            continue
        domain = grouped.setdefault(location.surface, {}).setdefault(
            location.domain,
            {"count": 0, "modules": {}},
        )
        domain["count"] += 1
        children = domain["modules"]
        path_parts: list[str] = []
        for segment in (
            _module_segments(location.module_path)
            if location.module_path else []
        ):
            path_parts.append(segment)
            node = children.setdefault(
                segment,
                {
                    "name": segment,
                    "path": "/".join(path_parts),
                    "count": 0,
                    "children": {},
                },
            )
            node["count"] += 1
            children = node["children"]

    def serialize_modules(nodes: dict[str, dict]) -> list[dict]:
        result = []
        for key in sorted(nodes):
            node = nodes[key]
            result.append({
                "name": node["name"],
                "path": node["path"],
                "count": node["count"],
                "children": serialize_modules(node["children"]),
            })
        return result

    result = []
    for surface_name in sorted(grouped, key=lambda name: SURFACE_ORDER.get(name, 99)):
        domains = []
        for domain_name in sorted(grouped[surface_name]):
            domain = grouped[surface_name][domain_name]
            domains.append({
                "domain": domain_name,
                "count": domain["count"],
                "modules": serialize_modules(domain["modules"]),
            })
        result.append({
            "surface": surface_name,
            "count": sum(domain["count"] for domain in grouped[surface_name].values()),
            "domains": domains,
        })
    return result


# ── helper ────────────────────────────────────────────

def _row_to_dict(r: TestCase) -> dict:
    location = canonical_case_location(r.domain, r.module, r.case_type)
    return {
        "id": r.id,
        "project_id": r.project_id,
        "case_id": r.case_id,
        "title": r.title,
        "domain": r.domain,
        "module": r.module,
        "case_type": r.case_type,
        "surface": location.surface,
        "taxonomy_domain": location.domain,
        "taxonomy_module": location.module_path,
        "terminal_scopes": list(location.terminal_scopes),
        "priority": r.priority,
        "status": r.status,
        "is_deleted": r.is_deleted,
        "tags": r.tags,
        "case_design_method": r.case_design_method,
        "positive_negative": r.positive_negative,
        "test_data_note": r.test_data_note,
        "preconditions": r.preconditions,
        "steps": r.steps,
        "expected_result": r.expected_result,
        "api_method": r.api_method,
        "api_endpoint": r.api_endpoint,
        "api_spec_ref": r.api_spec_ref,
        "api_headers": r.api_headers,
        "api_body": r.api_body,
        "api_assertions": r.api_assertions,
        "depends_on_ids": r.depends_on_ids,
        "last_response_json": r.last_response_json,
        "last_run_status": r.last_run_status,
        "dataset_id": getattr(r, "dataset_id", None),
        "source": r.source,
        "source_req_id": r.source_req_id,
        "source_doc_id": r.source_doc_id,
        "old_id": r.old_id,
        "review_status": r.review_status,
        "review_comment": r.review_comment,
        "reviewer_id": r.reviewer_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ── 域/模块分类管理 ───────────────────────────────────

def _domain_to_dict(d: TestCaseDomain) -> dict:
    return {"id": d.id, "domain": d.name, "count": 0, "modules": []}


def create_domain(db: Session, project_id: int, name: str) -> dict:
    """新增域。若同名域已被逻辑删除则恢复。"""
    existing = db.scalar(
        select(TestCaseDomain).where(
            TestCaseDomain.project_id == project_id,
            TestCaseDomain.name == name,
        )
    )
    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            db.commit()
            return _domain_to_dict(existing)
        raise ValueError(f"域 '{name}' 已存在")

    domain = TestCaseDomain(project_id=project_id, name=name)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return _domain_to_dict(domain)


def delete_domain(db: Session, domain_id: int, project_id: int) -> bool:
    """逻辑删除域、其所有模块，以及该域下所有用例。"""
    domain = db.scalar(
        select(TestCaseDomain).where(
            TestCaseDomain.id == domain_id,
            TestCaseDomain.project_id == project_id,
            TestCaseDomain.is_deleted.is_(False),
        )
    )
    if not domain:
        return False

    domain.is_deleted = True

    # 级联软删除关联模块
    modules = db.scalars(
        select(TestCaseModule).where(
            TestCaseModule.domain_id == domain_id,
            TestCaseModule.is_deleted.is_(False),
        )
    ).all()
    for m in modules:
        m.is_deleted = True

    # 级联软删除该域下所有用例
    case_rows = db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.domain == domain.name,
            TestCase.is_deleted.is_(False),
        )
    ).all()
    for c in case_rows:
        c.is_deleted = True

    db.commit()
    return True


def create_module(db: Session, domain_id: int, project_id: int, name: str) -> dict:
    """在指定域下新增模块。若同名模块已被逻辑删除则恢复。"""
    domain = db.scalar(
        select(TestCaseDomain).where(
            TestCaseDomain.id == domain_id,
            TestCaseDomain.project_id == project_id,
            TestCaseDomain.is_deleted.is_(False),
        )
    )
    if not domain:
        raise ValueError("所属域不存在")

    existing = db.scalar(
        select(TestCaseModule).where(
            TestCaseModule.domain_id == domain_id,
            TestCaseModule.name == name,
        )
    )
    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            db.commit()
            return {"id": existing.id, "module": existing.name, "count": 0}
        raise ValueError(f"模块 '{name}' 已存在")

    module = TestCaseModule(project_id=project_id, domain_id=domain_id, name=name)
    db.add(module)
    db.commit()
    db.refresh(module)
    return {"id": module.id, "module": module.name, "count": 0}


def delete_module(db: Session, domain_id: int, module_id: int) -> bool:
    """逻辑删除指定模块及其下所有用例。"""
    module = db.scalar(
        select(TestCaseModule).where(
            TestCaseModule.id == module_id,
            TestCaseModule.domain_id == domain_id,
            TestCaseModule.is_deleted.is_(False),
        )
    )
    if not module:
        return False

    # 获取模块名和域信息用于级联用例删除
    domain = db.scalar(
        select(TestCaseDomain).where(TestCaseDomain.id == domain_id)
    )
    module_name = module.name
    domain_name = domain.name if domain else ""

    module.is_deleted = True

    # 级联软删除该模块下所有用例
    case_rows = db.scalars(
        select(TestCase).where(
            TestCase.domain == domain_name,
            TestCase.module == module_name,
            TestCase.is_deleted.is_(False),
        )
    ).all()
    for c in case_rows:
        c.is_deleted = True

    db.commit()
    return True


def get_category_tree(db: Session, project_id: int) -> list[dict]:
    """返回域树，合并分类表（TestCaseDomain/TestCaseModule）和 TestCase 实际数据。

    - 分类表中的域/模块有 id，可被 CategoryManagerDialog 管理
    - TestCase 中的域/模块若不在分类表，作为只读条目保留在树中
    """
    # 1. 从分类表获取域和模块
    category_domains = db.scalars(
        select(TestCaseDomain).where(
            TestCaseDomain.project_id == project_id,
            TestCaseDomain.is_deleted.is_(False),
        )
    ).all()

    # 2. 从 TestCase 表获取实际模块用例数（排除已删除）
    case_rows = db.scalars(
        select(TestCase)
        .where(TestCase.project_id == project_id, TestCase.is_deleted.is_(False))
        .order_by(TestCase.domain, TestCase.module)
    ).all()

    module_counts: dict[tuple[str, str], int] = {}
    domain_names_from_cases: set[str] = set()
    for r in case_rows:
        key = (r.domain, r.module)
        module_counts[key] = module_counts.get(key, 0) + 1
        domain_names_from_cases.add(r.domain)

    seen_domains: set[str] = set()
    result = []

    # Add domains from category tables (with id)
    for d in category_domains:
        seen_domains.add(d.name)
        modules = db.scalars(
            select(TestCaseModule).where(
                TestCaseModule.domain_id == d.id,
                TestCaseModule.is_deleted.is_(False),
            )
        ).all()
        mod_list = []
        total = 0
        for m in modules:
            cnt = module_counts.get((d.name, m.name), 0)
            total += cnt
            mod_list.append({"id": m.id, "module": m.name, "count": cnt})
        result.append({"id": d.id, "domain": d.name, "count": total, "modules": mod_list})

    # Fallback: add domains from TestCase that aren't in category tables
    # Group by (domain, module) for TestCase-only domains
    domain_modules: dict[str, dict[str, int]] = {}
    for key, cnt in module_counts.items():
        domain, module = key
        if domain not in seen_domains:
            domain_modules.setdefault(domain, {})
            domain_modules[domain][module] = domain_modules[domain].get(module, 0) + cnt

    for domain in sorted(domain_modules):
        modules = domain_modules[domain]
        total = sum(modules.values())
        mod_list = [{"module": m, "count": c} for m, c in sorted(modules.items())]
        result.append({"domain": domain, "count": total, "modules": mod_list})

    _domain_order = {"用户端": 0, "运营后台": 1, "接口测试": 2}
    result.sort(key=lambda d: _domain_order.get(d["domain"], 99))
    return result
