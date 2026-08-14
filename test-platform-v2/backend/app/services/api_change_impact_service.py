"""接口变更影响分析服务 — 对比新旧 OpenAPI 文档，输出变更接口与受影响用例清单。

背景（XMind「测试流程与AI自动化」建议落地）：
- 被测系统版本迭代频繁（如体育平台 41 个版本），接口文档变动后，
  传统做法是全量重新生成用例，成本高且会覆盖人工优化的用例。
- 本服务：对比新旧 OpenAPI spec，识别新增/删除/修改的接口，
  并按接口路径匹配用例库中的 API 用例（TestCase.api_endpoint），
  输出「变更接口 → 受影响用例」清单与 AI 定向修改建议，实现增量维护。

变更分类：
- added     新接口（旧 spec 不存在）
- removed   已删除接口（新 spec 不存在）
- modified  接口存在但方法/路径参数/请求体/响应体/摘要有变化
- unchanged 无变化

影响级别：
- HIGH   接口删除（用例需下线）或请求/响应结构变更（断言可能失效）
- MEDIUM 接口摘要/描述变更（用例标题可更新，断言不受影响）
- LOW    仅 tags/模块推断变化
"""

from __future__ import annotations


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.services.openapi_import_service import _extract_endpoints

# 变更分类
CHANGE_ADDED = "added"
CHANGE_REMOVED = "removed"
CHANGE_MODIFIED = "modified"
CHANGE_UNCHANGED = "unchanged"

# 影响级别
IMPACT_HIGH = "HIGH"
IMPACT_MEDIUM = "MEDIUM"
IMPACT_LOW = "LOW"

# 对比时需要忽略的"软字段"（不影响用例的元信息）
_SOFT_FIELDS = {"summary", "description", "tags"}


def _endpoint_signature(ep: dict) -> tuple[str, str]:
    """接口唯一标识：(method, path)。"""
    return (ep.get("method", "").upper(), ep.get("path", ""))


def _endpoint_shape(ep: dict) -> dict:
    """接口的业务形状（剔除软字段），用于判断是否发生实质变更。"""
    return {k: v for k, v in ep.items() if k not in _SOFT_FIELDS}


def _spec_diff(old_endpoints: list[dict], new_endpoints: list[dict]) -> list[dict]:
    """对比新旧接口列表，输出变更清单。"""
    old_map = {_endpoint_signature(e): e for e in old_endpoints}
    new_map = {_endpoint_signature(e): e for e in new_endpoints}

    changes: list[dict] = []
    all_keys = sorted(set(old_map) | set(new_map), key=lambda k: (k[0], k[1]))

    for key in all_keys:
        old_ep = old_map.get(key)
        new_ep = new_map.get(key)
        if old_ep and not new_ep:
            changes.append(
                {
                    "method": key[0],
                    "path": key[1],
                    "change_type": CHANGE_REMOVED,
                    "impact": IMPACT_HIGH,
                    "summary": old_ep.get("summary", ""),
                    "detail": "接口已从新版本文档中移除，关联用例需下线或迁移",
                }
            )
        elif new_ep and not old_ep:
            changes.append(
                {
                    "method": key[0],
                    "path": key[1],
                    "change_type": CHANGE_ADDED,
                    "impact": IMPACT_MEDIUM,
                    "summary": new_ep.get("summary", ""),
                    "detail": "新版本新增接口，建议补充用例",
                }
            )
        else:
            old_shape = _endpoint_shape(old_ep)
            new_shape = _endpoint_shape(new_ep)
            if old_shape == new_shape:
                continue  # unchanged，不输出
            # 实质变更：找具体变化字段
            changed_fields = [
                f
                for f in sorted(set(old_shape) | set(new_shape))
                if old_shape.get(f) != new_shape.get(f)
            ]
            impact = _classify_impact(changed_fields)
            changes.append(
                {
                    "method": key[0],
                    "path": key[1],
                    "change_type": CHANGE_MODIFIED,
                    "impact": impact,
                    "summary": new_ep.get("summary", "") or old_ep.get("summary", ""),
                    "detail": f"字段变更: {', '.join(changed_fields)}",
                    "changed_fields": changed_fields,
                }
            )

    return changes


def _classify_impact(changed_fields: list[str]) -> str:
    """按变更字段判断影响级别。"""
    high_fields = {
        "request_schema",
        "response_schema",
        "deprecated",
        "auth_required",
    }
    if any(f in high_fields for f in changed_fields):
        return IMPACT_HIGH
    if changed_fields:
        return IMPACT_MEDIUM
    return IMPACT_LOW


def _match_cases(
    db: Session,
    project_id: int,
    changes: list[dict],
    *,
    case_module: str | None = None,
) -> dict:
    """将变更接口匹配到用例库中的 API 用例（按 api_method + api_endpoint 精确匹配）。

    返回 { (method,path): [case_dict, ...] }。
    """
    # 一次拉取项目下全部 API 用例，避免 N+1
    stmt = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.case_type == "api",
        TestCase.is_deleted.is_(False),
    )
    if case_module:
        stmt = stmt.where(TestCase.module == case_module)

    cases = db.scalars(stmt).all()

    # 归一化用例 endpoint：保留路径参数占位格式，兼容 {id} 与 :id
    def _norm(path: str) -> str:
        import re as _re

        return _re.sub(r"\{[^}]+\}", "{id}", path).rstrip("/")

    case_index: dict[tuple[str, str], list[dict]] = {}
    for c in cases:
        method = (c.api_method or "GET").upper()
        ep = _norm(c.api_endpoint or "")
        if not ep:
            continue
        case_index.setdefault((method, ep), []).append(
            {
                "case_id": c.id,
                "title": c.title or "",
                "module": c.module or "",
                "priority": c.priority or "",
                "api_method": method,
                "api_endpoint": c.api_endpoint or "",
            }
        )

    matched: dict[str, list[dict]] = {}
    for ch in changes:
        key = (ch["method"], _norm(ch["path"]))
        matched.setdefault(f"{ch['method']} {ch['path']}", [])
        if key in case_index:
            matched[f"{ch['method']} {ch['path']}"] = case_index[key]
    return matched


def analyze_openapi_change(
    db: Session,
    project_id: int,
    old_spec: dict,
    new_spec: dict,
    *,
    case_module: str | None = None,
) -> dict:
    """接口变更影响分析主入口。

    输入：旧/新 OpenAPI spec（dict）
    输出：变更统计 + 变更清单（含影响级别）+ 受影响用例清单 + 汇总建议。
    """
    old_endpoints = _extract_endpoints(old_spec)
    new_endpoints = _extract_endpoints(new_spec)

    changes = _spec_diff(old_endpoints, new_endpoints)
    affected_cases = _match_cases(db, project_id, changes, case_module=case_module)

    # 汇总
    stats = {
        "total_old": len(old_endpoints),
        "total_new": len(new_endpoints),
        "added": sum(1 for c in changes if c["change_type"] == CHANGE_ADDED),
        "removed": sum(1 for c in changes if c["change_type"] == CHANGE_REMOVED),
        "modified": sum(1 for c in changes if c["change_type"] == CHANGE_MODIFIED),
        "high_impact": sum(1 for c in changes if c["impact"] == IMPACT_HIGH),
        "affected_case_count": sum(len(v) for v in affected_cases.values()),
    }

    # 汇总建议（供 AI/人工定向修改参考）
    suggestions: list[str] = []
    if stats["removed"]:
        suggestions.append(
            f"有 {stats['removed']} 个接口已移除：对应用例应下线或迁移到替代接口"
        )
    if stats["added"]:
        suggestions.append(
            f"有 {stats['added']} 个新接口：建议按模块补充正向/边界/异常用例"
        )
    high_mod = [
        c
        for c in changes
        if c["change_type"] == CHANGE_MODIFIED and c["impact"] == IMPACT_HIGH
    ]
    if high_mod:
        paths = ", ".join(f"{c['method']} {c['path']}" for c in high_mod[:5])
        suggestions.append(
            f"有 {len(high_mod)} 个接口发生请求/响应结构变更（如 {paths}）："
            f"关联用例的断言与请求体需定向更新"
        )

    return {
        "stats": stats,
        "changes": changes,
        "affected_cases": affected_cases,
        "suggestions": suggestions,
    }


def changes_to_markdown(result: dict) -> str:
    """将变更分析结果渲染为 Markdown（便于报告/人工核查）。"""
    lines = [
        "# 接口变更影响分析报告",
        "",
        "## 统计",
        "",
        f"- 旧文档接口数: {result['stats']['total_old']}",
        f"- 新文档接口数: {result['stats']['total_new']}",
        f"- 新增: {result['stats']['added']} / 移除: {result['stats']['removed']} / "
        f"修改: {result['stats']['modified']}",
        f"- 高影响: {result['stats']['high_impact']} / "
        f"受影响用例: {result['stats']['affected_case_count']}",
        "",
        "## 变更清单",
        "",
        "| 类型 | 方法 | 路径 | 影响 | 说明 |",
        "|------|------|------|------|------|",
    ]
    for c in result["changes"]:
        lines.append(
            f"| {c['change_type']} | {c['method']} | `{c['path']}` | "
            f"{c['impact']} | {c['detail']} |"
        )
    lines += ["", "## 受影响用例", ""]
    for key, cases in result["affected_cases"].items():
        if not cases:
            continue
        lines.append(f"### {key}")
        for c in cases:
            lines.append(
                f"- #{c['case_id']} [{c['priority']}] {c['title']} "
                f"(模块: {c['module']})"
            )
        lines.append("")
    if result["suggestions"]:
        lines += ["## 修改建议", ""]
        for s in result["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")
    return "\n".join(lines)
