"""接口测试用例生成引擎 — 基于接口 schema 生成正向/边界/异常/幂等用例。"""
from __future__ import annotations

import copy
import json
from typing import Any


def generate_cases_from_endpoint(
    endpoint: dict,
    *,
    templates: list[str] | None = None,
) -> list[dict]:
    """从接口定义生成测试用例列表。

    Args:
        endpoint: {service_name, module, method, path, summary, request_schema}
        templates: 生成模板集 [basic, boundary, invalid, idempotency]

    Returns:
        list of case dicts with title/domain/module/case_type/priority/steps/
        expected_result/api_method/api_endpoint/api_headers/api_body/api_assertions/tags
    """
    if templates is None:
        templates = ["basic"]

    cases: list[dict] = []
    schema = endpoint.get("request_schema", {})
    body_schema = schema.get("body", {}) if isinstance(schema, dict) else {}
    properties = body_schema.get("properties", {})
    required_fields = body_schema.get("required", [])

    method = endpoint.get("method", "GET").upper()
    path = endpoint.get("path", "")
    module = endpoint.get("module", "")
    service = endpoint.get("service_name", "")
    summary = endpoint.get("summary", "")

    # ── 基础正常用例 ──
    if "basic" in templates:
        cases.append(_build_positive_case(endpoint))
        # 如果接口有 query 参数，额外加参数组合用例
        query_params = schema.get("query", []) if isinstance(schema, dict) else []
        if query_params:
            cases.append(_build_query_param_case(endpoint, query_params))

    # ── 必填字段校验 ──
    if "invalid" in templates and required_fields:
        cases.extend(_build_required_cases(endpoint, required_fields, properties))

    # ── 类型校验 ──
    if "invalid" in templates and properties:
        cases.extend(_build_type_cases(endpoint, properties))

    # ── 枚举校验 ──
    if "invalid" in templates and properties:
        cases.extend(_build_enum_cases(endpoint, properties))

    # ── 边界值 ──
    if "boundary" in templates and properties:
        cases.extend(_build_boundary_cases(endpoint, properties))

    # ── 格式校验 ──
    if "invalid" in templates and properties:
        cases.extend(_build_format_cases(endpoint, properties))

    # ── 幂等 ──
    if "idempotency" in templates:
        cases.extend(_build_idempotency_cases(endpoint))

    # ── 认证 ──
    if "invalid" in templates:
        cases.append(_build_auth_missing_case(endpoint))

    return cases


# ═══════════════════════════════════════════════════════
# 基础正常用例
# ═══════════════════════════════════════════════════════

def _build_positive_case(ep: dict) -> dict:
    """构造正向基础用例。"""
    body = _build_valid_body(ep)
    return _make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 正常请求",
        priority="P0",
        scenario="positive",
        body=body,
        assertions=[
            {"type": "status_code", "expected": 0, "operator": "neq"},  # 非 5xx（宽松断言）
            {"type": "response_time", "expected": 5000, "operator": "lt"},
        ],
        expected="接口返回非 5xx 状态码，响应时间 < 5s。",
    )


def _build_query_param_case(ep: dict, query_params: list) -> dict:
    """构造 query 参数组合用例。"""
    params = {p["name"]: _sample_value_for_param(p) for p in query_params if p.get("required")}
    query_str = "&".join(f"{k}={v}" for k, v in params.items())
    full_path = f"{ep['path']}?{query_str}"

    c = _make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 带 Query 参数",
        priority="P1",
        scenario="positive",
        body=_build_valid_body(ep),
        assertions=[
            {"type": "status_code", "expected": 0, "operator": "neq"},
        ],
        expected="正确传入 query 参数时返回 2xx。",
    )
    c["api_endpoint"] = full_path
    return c


# ═══════════════════════════════════════════════════════
# 必填字段校验
# ═══════════════════════════════════════════════════════

def _build_required_cases(ep: dict, required_fields: list, properties: dict) -> list[dict]:
    """为每个必填字段生成缺失/null/空字符串用例。"""
    cases = []
    for field in required_fields:
        prop = properties.get(field, {})
        ptype = prop.get("type", "string")

        # 缺失字段
        body_missing = _build_valid_body(ep, exclude_fields=[field])
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 必填缺失",
            priority="P1",
            scenario="required_missing",
            body=body_missing,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "neq"},  # 期望非 2xx
                {"type": "status_code", "expected": 500, "operator": "neq"},  # 也不应 5xx
            ],
            expected=f"缺少必填字段 {field}，应返回 4xx 参数校验错误。",
        ))

        # null 值
        body_null = _build_valid_body(ep, overrides={field: None})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 为 null",
            priority="P1",
            scenario="required_null",
            body=body_null,
            assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
            expected=f"必填字段 {field} 为 null 时应返回 4xx。",
        ))

        # 空字符串（仅 string 类型）
        if ptype == "string":
            body_empty = _build_valid_body(ep, overrides={field: ""})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 为空字符串",
                priority="P2",
                scenario="required_empty",
                body=body_empty,
                assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                expected=f"必填字段 {field} 为空字符串时应返回 4xx。",
            ))

    return cases


# ═══════════════════════════════════════════════════════
# 类型校验
# ═══════════════════════════════════════════════════════

_TYPE_MISMATCH_MAP = {
    "string": ["12345", "true"],
    "integer": ["not_a_number", "3.14"],
    "number": ["not_a_number", "true"],
    "boolean": ["not_bool", "123"],
    "array": ['{"not":"array"}'],
    "object": ["not_an_object"],
}

def _build_type_cases(ep: dict, properties: dict) -> list[dict]:
    """为可写接口字段生成类型错误用例。"""
    method = ep.get("method", "GET").upper()
    if method not in ("POST", "PUT", "PATCH"):
        return []

    cases = []
    for field, prop in properties.items():
        ptype = prop.get("type", "string")
        mismatches = _TYPE_MISMATCH_MAP.get(ptype, ["__invalid__"])
        for bad_val in mismatches[:2]:  # 每个字段最多 2 条
            body = _build_valid_body(ep, overrides={field: bad_val})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 类型错误({ptype}←{type(bad_val).__name__})",
                priority="P2",
                scenario="type_error",
                body=body,
                assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                expected=f"{field} 类型不匹配时应返回 4xx 参数校验错误。",
            ))
    return cases


# ═══════════════════════════════════════════════════════
# 枚举校验
# ═══════════════════════════════════════════════════════

def _build_enum_cases(ep: dict, properties: dict) -> list[dict]:
    """为枚举字段生成合法值和非法值用例。"""
    cases = []
    for field, prop in properties.items():
        enum_vals = prop.get("enum", [])
        if not enum_vals:
            continue
        # 非法枚举值
        body = _build_valid_body(ep, overrides={field: "___INVALID_ENUM_VALUE___"})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 枚举非法值",
            priority="P1",
            scenario="enum_invalid",
            body=body,
            assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
            expected=f"{field} 传入非法枚举值时应返回 4xx。",
        ))
    return cases


# ═══════════════════════════════════════════════════════
# 边界值
# ═══════════════════════════════════════════════════════

def _build_boundary_cases(ep: dict, properties: dict) -> list[dict]:
    """为 string/integer 字段生成边界值用例。"""
    cases = []
    for field, prop in properties.items():
        ptype = prop.get("type", "string")

        if ptype == "string":
            min_len = prop.get("minLength")
            max_len = prop.get("maxLength")
            if min_len is not None and min_len > 0:
                # minLength - 1（应失败）
                short_val = "a" * (min_len - 1)
                body = _build_valid_body(ep, overrides={field: short_val})
                cases.append(_make_case(
                    ep,
                    title=f"{ep.get('summary') or ep.get('path')} - {field} 最小长度-1 ({min_len - 1})",
                    priority="P2",
                    scenario="boundary_min",
                    body=body,
                    assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                    expected=f"{field} 小于 minLength 应返回 4xx。",
                ))
                # minLength（应成功）
                ok_val = "a" * min_len
                body_ok = _build_valid_body(ep, overrides={field: ok_val})
                cases.append(_make_case(
                    ep,
                    title=f"{ep.get('summary') or ep.get('path')} - {field} 最小长度({min_len})",
                    priority="P1",
                    scenario="boundary_valid",
                    body=body_ok,
                    assertions=[{"type": "status_code", "expected": 500, "operator": "lt"}],
                    expected=f"{field} 等于 minLength 应正常处理。",
                ))
            if max_len is not None:
                # maxLength + 1（应失败）
                long_val = "a" * (max_len + 1)
                body = _build_valid_body(ep, overrides={field: long_val})
                cases.append(_make_case(
                    ep,
                    title=f"{ep.get('summary') or ep.get('path')} - {field} 最大长度+1 ({max_len + 1})",
                    priority="P2",
                    scenario="boundary_max",
                    body=body,
                    assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                    expected=f"{field} 超过 maxLength 应返回 4xx。",
                ))

        elif ptype in ("integer", "number"):
            minimum = prop.get("minimum")
            maximum = prop.get("maximum")
            if minimum is not None:
                body = _build_valid_body(ep, overrides={field: minimum - 1})
                cases.append(_make_case(
                    ep,
                    title=f"{ep.get('summary') or ep.get('path')} - {field} 最小值-1 ({minimum - 1})",
                    priority="P2",
                    scenario="boundary_min",
                    body=body,
                    assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                    expected=f"{field} 小于 minimum 应返回 4xx。",
                ))
            if maximum is not None:
                body = _build_valid_body(ep, overrides={field: maximum + 1})
                cases.append(_make_case(
                    ep,
                    title=f"{ep.get('summary') or ep.get('path')} - {field} 最大值+1 ({maximum + 1})",
                    priority="P2",
                    scenario="boundary_max",
                    body=body,
                    assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                    expected=f"{field} 超过 maximum 应返回 4xx。",
                ))

    return cases


# ═══════════════════════════════════════════════════════
# 格式校验
# ═══════════════════════════════════════════════════════

def _build_format_cases(ep: dict, properties: dict) -> list[dict]:
    """为 format 字段生成格式错误用例。"""
    cases = []
    for field, prop in properties.items():
        fmt = prop.get("format", "")
        bad_value = None
        if fmt == "email":
            bad_value = "not-an-email"
        elif fmt in ("uri", "url"):
            bad_value = "not_a_url"
        elif fmt == "date":
            bad_value = "not-a-date"
        elif fmt == "date-time":
            bad_value = "not-a-datetime"
        if bad_value:
            body = _build_valid_body(ep, overrides={field: bad_value})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 格式错误({fmt})",
                priority="P2",
                scenario="format_error",
                body=body,
                assertions=[{"type": "status_code", "expected": 200, "operator": "neq"}],
                expected=f"{field} 格式不符合 {fmt} 时应返回 4xx。",
            ))
    return cases


# ═══════════════════════════════════════════════════════
# 幂等
# ═══════════════════════════════════════════════════════

def _build_idempotency_cases(ep: dict) -> list[dict]:
    """为写接口生成幂等用例。"""
    method = ep.get("method", "GET").upper()
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return []

    body = _build_valid_body(ep)
    cases = [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 幂等-重复提交",
            priority="P1",
            scenario="idempotency",
            body=body,
            assertions=[{"type": "status_code", "expected": 500, "operator": "lt"}],
            expected="重复提交同一请求应返回幂等结果或合理的业务错误，不产生重复数据。",
            extra_headers={"Idempotency-Key": "test-idempotency-key-001"},
        ),
    ]

    if method == "DELETE":
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 幂等-重复删除",
            priority="P2",
            scenario="idempotency",
            body=body,
            assertions=[{"type": "status_code", "expected": 500, "operator": "lt"}],
            expected="重复删除应返回 404 或成功，不应 5xx。",
        ))

    return cases


# ═══════════════════════════════════════════════════════
# 认证缺失
# ═══════════════════════════════════════════════════════

def _build_auth_missing_case(ep: dict) -> dict:
    """构造无 token 用例。"""
    return _make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 缺少认证 Token",
        priority="P1",
        scenario="auth_missing",
        body=_build_valid_body(ep),
        assertions=[{"type": "status_code", "expected": 401, "operator": "eq"}],
        expected="无 token 时应返回 401。",
        extra_headers={},  # 不传 Authorization
        strip_auth=True,
    )


# ═══════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════

def _make_case(
    ep: dict,
    *,
    title: str,
    priority: str,
    scenario: str,
    body: dict | str,
    assertions: list[dict],
    expected: str,
    extra_headers: dict | None = None,
    strip_auth: bool = False,
) -> dict:
    """构造统一的用例 dict。"""
    method = ep.get("method", "GET").upper()
    path = ep.get("path", "")
    service = ep.get("service_name", "")
    module = ep.get("module", "")

    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    body_str = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)

    # 对于 GET/HEAD/DELETE 等请求，body 通常为空
    if method in ("GET", "HEAD"):
        body_str = ""

    return {
        "title": title,
        "domain": "接口测试",
        "module": module,
        "case_type": "api",
        "priority": priority,
        "preconditions": f"接口 {method} {path} 可访问",
        "steps": [
            {"step": 1, "action": f"发送 {method} 请求到 {path}", "expected": expected},
        ],
        "expected_result": expected,
        "api_method": method,
        "api_endpoint": path,
        "api_headers": headers,
        "api_body": body_str,
        "api_assertions": assertions,
        "source": "ai_generated",
        "tags": [
            f"service:{service}",
            f"scenario:{scenario}",
            f"source:ai_generated",
        ],
    }


def _build_valid_body(ep: dict, exclude_fields: list[str] | None = None, overrides: dict | None = None) -> dict:
    """根据 schema 构造合法的请求体。"""
    schema = ep.get("request_schema", {})
    if isinstance(schema, dict):
        body_schema = schema.get("body", {})
    else:
        body_schema = {}

    properties = body_schema.get("properties", {})
    body = {}
    exclude = set(exclude_fields or [])

    for field, prop in properties.items():
        if field in exclude:
            continue
        body[field] = _sample_value_for_prop(prop)

    if overrides:
        body.update(overrides)

    return body


def _sample_value_for_prop(prop: dict) -> Any:
    """根据属性定义生成样本值。"""
    ptype = prop.get("type", "string")

    if "enum" in prop:
        return prop["enum"][0]

    if ptype == "string":
        fmt = prop.get("format", "")
        if fmt == "email":
            return "test@example.com"
        if fmt in ("uri", "url"):
            return "https://example.com"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        min_len = prop.get("minLength", 1)
        return "t" * max(min_len, 3)
    elif ptype == "integer":
        minimum = prop.get("minimum", 1)
        return max(minimum, 1)
    elif ptype == "number":
        minimum = prop.get("minimum", 0)
        return float(max(minimum, 1))
    elif ptype == "boolean":
        return True
    elif ptype == "array":
        items = prop.get("items", {})
        return [_sample_value_for_prop(items)] if items else []
    elif ptype == "object":
        return {}
    return "test"


def _sample_value_for_param(param: dict) -> Any:
    """为 query/path 参数生成样本值。"""
    return _sample_value_for_prop(param)
