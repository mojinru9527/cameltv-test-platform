"""手工用例 → API 用例泛化服务（C-API-AUTO-004）。

背景（XMind「测试流程与AI自动化」建议落地）：
- 测试团队先有丰富的手工功能用例（描述业务操作），接口文档/接口资产后到。
- 传统做法：接口资产到齐后全量重新设计 API 用例，重复劳动。
- 本服务：以「同模块手工用例 + 接口资产」为输入，把手工用例的业务操作
  泛化为对应 API 用例（api_method/api_endpoint/api_headers/api_body/api_assertions），
  实现「手工用例 → API 用例」的复用路径。

两种模式：
- rule（默认，确定性）：从手工用例步骤中识别业务操作动词（查询/列表/新增/
  修改/删除/详情），映射到同模块接口资产生成 API 用例骨架 + 基础断言。
  无需 AI key，结果稳定可复核。
- ai（增强）：在 rule 结果基础上，调用 LLM 补全请求体样例与断言细节
  （需配置 AI_API_KEY；失败自动降级 rule 结果）。

输入：
- 手工用例：TestCase 中 case_type='manual'（含 steps/preconditions/expected_result）
- 接口资产：ApiEndpoint（同 module 的 method/path/request_schema）
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_asset import ApiEndpoint
from app.models.test_case import TestCase

# ── 业务操作动词 → HTTP 方法 映射（规则模式核心） ──
_VERB_METHOD: dict[str, str] = {
    # 查询类
    "查询": "GET",
    "查看": "GET",
    "搜索": "GET",
    "获取": "GET",
    "列表": "GET",
    "详情": "GET",
    "导出": "GET",
    "分页": "GET",
    # 新增类
    "新增": "POST",
    "创建": "POST",
    "添加": "POST",
    "上传": "POST",
    "注册": "POST",
    "登录": "POST",
    "提交": "POST",
    # 修改类
    "修改": "PUT",
    "更新": "PUT",
    "编辑": "PUT",
    "保存": "PUT",
    # 删除类
    "删除": "DELETE",
    "移除": "DELETE",
    "取消": "DELETE",
}
# 需要路径参数的动词（详情/删除/修改通常针对单个资源）
_NEED_PATH_PARAM = {"详情", "删除", "移除", "修改", "更新", "编辑"}


def _safe_json(raw: str, default: Any = None) -> Any:
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def pick_manual_cases(
    db: Session,
    project_id: int,
    *,
    module: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """选取项目下的手工功能用例（含步骤），可按模块过滤。"""
    stmt = (
        select(TestCase)
        .where(
            TestCase.project_id == project_id,
            TestCase.case_type == "manual",
            TestCase.is_deleted.is_(False),
        )
        .order_by(TestCase.id)
        .limit(limit)
    )
    if module:
        stmt = stmt.where(TestCase.module == module)

    out: list[dict] = []
    for c in db.scalars(stmt).all():
        out.append(
            {
                "id": c.id,
                "title": c.title or "",
                "module": c.module or "",
                "priority": c.priority or "",
                "preconditions": c.preconditions or "",
                "steps": _safe_json(c.steps, []),
                "expected_result": c.expected_result or "",
            }
        )
    return out


def match_endpoints(
    db: Session,
    project_id: int,
    *,
    module: str | None = None,
) -> list[dict]:
    """匹配同模块接口资产（可按模块过滤）。"""
    stmt = (
        select(ApiEndpoint)
        .where(ApiEndpoint.project_id == project_id)
        .order_by(ApiEndpoint.id)
    )
    if module:
        stmt = stmt.where(ApiEndpoint.module == module)

    out: list[dict] = []
    for ep in db.scalars(stmt).all():
        out.append(
            {
                "id": ep.id,
                "module": ep.module or "",
                "method": ep.method or "GET",
                "path": ep.path or "",
                "summary": ep.summary or "",
                "request_schema": _safe_json(ep.request_schema, {}),
            }
        )
    return out


def _detect_verb(steps: list[dict]) -> str:
    """从手工用例步骤文本中识别业务操作动词；未识别返回空串。"""
    texts: list[str] = []
    for s in steps:
        if isinstance(s, dict):
            action = s.get("action") or s.get("desc") or s.get("expected") or ""
            texts.append(str(action))
        elif isinstance(s, str):
            texts.append(s)
    blob = " ".join(texts)
    # 详情语义：文本含"详情"即视为单资源操作（需要路径参数）
    if "详情" in blob:
        return "详情"
    for verb in _VERB_METHOD:  # 遍历顺序即优先级
        if verb in blob:
            return verb
    return ""


def _match_endpoint(endpoints: list[dict], verb: str, title: str) -> dict | None:
    """按动词映射的方法 + 路径关键词匹配接口资产。"""
    method = _VERB_METHOD.get(verb, "GET")
    # 路径关键词：取用例标题中的实体词（去掉操作动词与标点）
    import re

    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z]+", title)
    keywords = [t for t in tokens if t not in _VERB_METHOD][:3]

    # 优先：方法匹配 + 路径含关键词
    method_candidates = [ep for ep in endpoints if ep["method"].upper() == method]
    if keywords:
        for kw in keywords:
            for ep in method_candidates:
                if kw.lower() in ep["path"].lower():
                    return ep
    # 次优：仅方法匹配
    if method_candidates:
        return method_candidates[0]
    # 兜底：任意接口
    return endpoints[0] if endpoints else None


def _build_rule_case(manual: dict, endpoint: dict | None, verb: str) -> dict | None:
    """规则模式：手工用例 + 接口资产 → API 用例骨架。"""
    if not endpoint:
        return None
    method = _VERB_METHOD.get(verb, "GET")
    path = endpoint["path"]

    # 需要路径参数的操作：替换 {id} 占位
    if verb in _NEED_PATH_PARAM and "{id}" in path:
        path = path.replace("{id}", "1")

    # 基础断言
    assertions: list[dict] = [
        {"type": "status_code", "expected": 200, "operator": "gte"},
        {"type": "status_code", "expected": 300, "operator": "lt"},
    ]

    # 请求体：有 schema 时给空 body（规则模式不猜测值，避免无意义占位）
    body = ""
    if method in ("POST", "PUT", "PATCH"):
        schema = endpoint.get("request_schema") or {}
        body_schema = schema.get("body", {}) if isinstance(schema, dict) else {}
        if body_schema:
            body = "{}"  # 空对象，AI 模式会补全；规则模式交由用户完善

    return {
        "title": f"[泛化] {manual['title']}",
        "domain": "接口测试",
        "module": endpoint.get("module") or manual.get("module") or "",
        "case_type": "api",
        "priority": manual.get("priority") or "P2",
        "preconditions": (
            f"接口 {method} {path} 可访问；来源手工用例 #{manual.get('id')}"
        ),
        "steps": [
            {
                "step": 1,
                "action": f"发送 {method} 请求到 {path}",
                "expected": "接口正常响应",
            },
        ],
        "expected_result": manual.get("expected_result") or "接口响应符合预期",
        "api_method": method,
        "api_endpoint": path,
        "api_headers": {"Content-Type": "application/json"},
        "api_body": body,
        "api_assertions": assertions,
        "case_design_method": "manual-to-api-generalization",
        "positive_negative": "positive",
        "test_data_note": (
            f"由手工用例 #{manual.get('id')}「{manual['title']}」"
            "泛化生成（规则模式）"
        ),
        "source": "ai_generated",
        "tags": ["source:manual-generalization", f"manual_case:{manual.get('id')}"],
    }


def generalize_cases(
    db: Session,
    project_id: int,
    *,
    module: str | None = None,
    mode: str = "rule",
    limit: int = 200,
) -> dict:
    """手工用例 → API 用例泛化主入口。

    Args:
        mode: "rule"（确定性规则）| "ai"（规则 + AI 增强，需 AI_API_KEY）
    Returns:
        {total_manual, matched, generated: [...], unmatched: [...], mode}
    """
    manual_cases = pick_manual_cases(db, project_id, module=module, limit=limit)
    endpoints = match_endpoints(db, project_id, module=module)

    generated: list[dict] = []
    unmatched: list[dict] = []

    for manual in manual_cases:
        steps = manual.get("steps") or []
        verb = _detect_verb(steps)
        if not verb:
            # 无步骤文本时尝试从标题识别
            verb = _detect_verb([{"action": manual.get("title", "")}])
        endpoint = _match_endpoint(endpoints, verb, manual.get("title", ""))
        case = _build_rule_case(manual, endpoint, verb)
        if case:
            generated.append(case)
        else:
            unmatched.append(
                {
                    "manual_case_id": manual.get("id"),
                    "title": manual.get("title", ""),
                    "reason": "未匹配到接口资产" if not endpoint else "未识别业务操作",
                }
            )

    result = {
        "total_manual": len(manual_cases),
        "matched_endpoints": len(endpoints),
        "generated": generated,
        "generated_count": len(generated),
        "unmatched": unmatched,
        "mode": mode,
    }

    if mode == "ai":
        _enhance_with_ai(result)

    return result


def _enhance_with_ai(result: dict) -> None:
    """AI 增强：为生成的用例补全请求体样例与断言细节。

    依赖 settings.ai_api_key；未配置或调用失败时静默保留规则结果（降级）。
    """
    from app.core.config import settings

    if not settings.ai_api_key:
        # 未配置 AI key：降级为 rule 模式（result["mode"] 原为请求值 "ai"）
        result["mode"] = "rule"
        return
    if not result["generated"]:
        return
    try:
        from app.services.ai_service import _call_ai_api

        import asyncio

        payloads = []
        for case in result["generated"]:
            payloads.append(
                {
                    "method": case["api_method"],
                    "path": case["api_endpoint"],
                    "title": case["title"],
                    "body": case.get("api_body", ""),
                }
            )

        system_prompt = (
            "你是资深接口测试工程师。根据每个接口的方法、路径与用例标题，"
            '输出 JSON 数组，每项为 {"api_body": <合法JSON请求体或"">, '
            '"api_assertions": [{"type": "jsonpath", "path": "$.xxx", '
            '"operator": "exists", "expected": true}]}。'
            "请求体必须是有业务含义的样例值，禁止无意义占位；不确定时给空字符串。"
        )
        user_message = json.dumps(payloads, ensure_ascii=False)

        raw = asyncio.run(
            _call_ai_api(system_prompt, user_message, "manual-api-generalization")
        )
        parsed = _parse_ai_array(raw)
        for case, extra in zip(result["generated"], parsed):
            if not extra:
                continue
            if extra.get("api_body"):
                case["api_body"] = extra["api_body"]
            if extra.get("api_assertions"):
                case["api_assertions"] = extra["api_assertions"]
            case["test_data_note"] = (
                "由手工用例泛化生成（AI 增强模式）；"
                "请求体/断言由 LLM 补全，需人工复核"
            )
        result["mode"] = "ai"
    except Exception:
        # AI 增强失败降级为规则结果，不阻断
        result["mode"] = "rule"


def _parse_ai_array(raw: Any) -> list[dict]:
    """解析 AI 返回的 JSON 数组（兼容外层 dict 包装）。"""
    if isinstance(raw, dict):
        raw = raw.get("content") or raw.get("result") or raw.get("data") or ""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            # 提取 JSON 数组片段
            start = raw.find("[")
            end = raw.rfind("]")
            if start >= 0 and end > start:
                try:
                    raw = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return []
            else:
                return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def create_generated_cases(
    db: Session,
    project_id: int,
    cases: list[dict],
) -> list[int]:
    """将泛化生成的用例入库，返回用例 ID 列表。"""
    from app.services.api_case_generation_service import create_test_case_from_generated

    ids: list[int] = []
    for c in cases:
        tc = create_test_case_from_generated(db, project_id, c, None)
        ids.append(tc.id)
    db.commit()
    return ids
