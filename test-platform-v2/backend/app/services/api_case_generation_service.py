"""接口测试用例生成引擎 — 基于接口 schema 生成正向/边界/异常/幂等/极限用例。"""
from __future__ import annotations

import copy
import json
from typing import Any

# 单接口用例生成数量上限（防止膨胀）
_MAX_CASES_PER_ENDPOINT = 200


def generate_cases_from_endpoint(
    endpoint: dict,
    *,
    templates: list[str] | None = None,
) -> list[dict]:
    """从接口定义生成测试用例列表。

    Args:
        endpoint: {service_name, module, method, path, summary, request_schema}
        templates: 生成模板集 [basic, boundary, invalid, idempotency, extreme]

    Returns:
        list of case dicts with title/domain/module/case_type/priority/steps/
        expected_result/api_method/api_endpoint/api_headers/api_body/api_assertions/tags
    """
    if templates is None:
        templates = ["basic", "boundary", "invalid", "security", "idempotency", "extreme"]

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

    # Extract query/path/header params
    query_params = schema.get("query", []) if isinstance(schema, dict) else []
    path_params = schema.get("path", []) if isinstance(schema, dict) else []
    header_params = schema.get("header", []) if isinstance(schema, dict) else []

    # ── 基础正常用例 ──
    if "basic" in templates:
        cases.append(_build_positive_case(endpoint))
        if query_params:
            cases.append(_build_query_param_case(endpoint, query_params))

    # ── 必填字段校验 (body) ──
    if "invalid" in templates and required_fields:
        cases.extend(_build_required_cases(endpoint, required_fields, properties))

    # ── 类型校验 (body) ──
    if "invalid" in templates and properties:
        cases.extend(_build_type_cases(endpoint, properties))

    # ── 枚举校验 (body) ──
    if "invalid" in templates and properties:
        cases.extend(_build_enum_cases(endpoint, properties))

    # ── 边界值 (body) ──
    if "boundary" in templates and properties:
        cases.extend(_build_boundary_cases(endpoint, properties))

    # ── 格式校验 (body) ──
    if "invalid" in templates and properties:
        cases.extend(_build_format_cases(endpoint, properties))

    # ── Query 参数校验 ──
    if "invalid" in templates and query_params:
        cases.extend(_build_query_required_cases(endpoint, query_params))
        cases.extend(_build_query_type_cases(endpoint, query_params))
    if "extreme" in templates and query_params:
        cases.extend(_build_query_injection_cases(endpoint, query_params))

    # ── Path 参数校验 ──
    if path_params:
        if "invalid" in templates:
            cases.extend(_build_path_param_cases(endpoint, path_params))

    # ── Header 校验 ──
    if "invalid" in templates and header_params:
        cases.extend(_build_header_param_cases(endpoint, header_params))

    # ── 极徛/特殊字符 (body) ──
    if "extreme" in templates and properties:
        cases.extend(_build_extreme_cases(endpoint, properties))

    # ── 安全注入 ──
    if "security" in templates and properties:
        cases.extend(_build_security_cases(endpoint, properties))

    # ── 幂等 ──
    if "idempotency" in templates:
        cases.extend(_build_idempotency_cases(endpoint))

    # ── 认证 ──
    if "invalid" in templates:
        cases.append(_build_auth_missing_case(endpoint))

    # ── 数量上限保护 ──
    if len(cases) > _MAX_CASES_PER_ENDPOINT:
        cases = cases[:_MAX_CASES_PER_ENDPOINT]

    return cases


# ═══════════════════════════════════════════════════════
# 基础正常用例
# ═══════════════════════════════════════════════════════

def _build_positive_case(ep: dict) -> dict:
    """构造正向基础用例。断言 status_code 在 2xx 范围。"""
    body = _build_valid_body(ep)
    return _make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 正常请求",
        priority="P0",
        scenario="positive",
        body=body,
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},   # >=200
            {"type": "status_code", "expected": 300, "operator": "lt"},    # <300 = 2xx
            {"type": "response_time", "expected": 5000, "operator": "lt"},
        ],
        expected="接口返回 2xx 状态码，响应时间 < 5s。",
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
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 300, "operator": "lt"},
        ],
        expected="正确传入 query 参数时返回 2xx。",
    )
    c["api_endpoint"] = full_path
    return c


# ═══════════════════════════════════════════════════════
# 必填字段校验
# ═══════════════════════════════════════════════════════

def _build_required_cases(ep: dict, required_fields: list, properties: dict) -> list[dict]:
    """为每个必填字段生成缺失/null/空字符串用例。断言 4xx 范围，避免 2xx/3xx 假通过。"""
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
                {"type": "status_code", "expected": 400, "operator": "gte"},  # >=400
                {"type": "status_code", "expected": 500, "operator": "lt"},   # <500 = 4xx
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
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
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
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
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
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
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
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
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
                    assertions=[
                        {"type": "status_code", "expected": 400, "operator": "gte"},
                        {"type": "status_code", "expected": 500, "operator": "lt"},
                    ],
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
                    assertions=[
                        {"type": "status_code", "expected": 200, "operator": "gte"},
                        {"type": "status_code", "expected": 300, "operator": "lt"},
                    ],
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
                    assertions=[
                        {"type": "status_code", "expected": 400, "operator": "gte"},
                        {"type": "status_code", "expected": 500, "operator": "lt"},
                    ],
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
                    assertions=[
                        {"type": "status_code", "expected": 400, "operator": "gte"},
                        {"type": "status_code", "expected": 500, "operator": "lt"},
                    ],
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
                    assertions=[
                        {"type": "status_code", "expected": 400, "operator": "gte"},
                        {"type": "status_code", "expected": 500, "operator": "lt"},
                    ],
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
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
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
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
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
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
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
# 极限/特殊字符
# ═══════════════════════════════════════════════════════

# 常见攻击 payload
_SQL_INJECTION_PAYLOADS = [
    "'; DROP TABLE users; --",
    "' OR '1'='1",
    "1; SELECT * FROM users",
    "1' UNION SELECT NULL--",
]
_XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
]
_SPECIAL_CHARACTERS = [
    "\x00null_byte",
    "\t\n\r",
    "   ",  # 纯空白
    "!@#$%^&*()_+-=[]{}|;':\",./<>?",
    "中文测试字符😀🎯",
]


def _build_extreme_cases(ep: dict, properties: dict) -> list[dict]:
    """为 string 字段生成超长字符串、SQL/XSS、特殊字符用例。

    仅对 POST/PUT/PATCH 等写接口生成，避免 GET 请求中误用。
    """
    method = ep.get("method", "GET").upper()
    if method not in ("POST", "PUT", "PATCH"):
        return []

    cases = []
    string_fields = [
        f for f, p in properties.items()
        if p.get("type") == "string"
    ]

    if not string_fields:
        return []

    # 取前 2 个 string 字段生成（避免爆炸）
    for field in string_fields[:2]:
        prop = properties.get(field, {})
        max_len = prop.get("maxLength")

        # 超长字符串（如果有 maxLength 约束）
        if max_len is not None and max_len > 0:
            long_val = "A" * (max_len + 100)
            body = _build_valid_body(ep, overrides={field: long_val})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 超长({max_len + 100}字符)",
                priority="P2",
                scenario="extreme_long",
                body=body,
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{field} 超过 maxLength {max_len} 时应返回 4xx。",
            ))
        else:
            # 没有 maxLength 约束，测试 10000 字符
            long_val = "A" * 10000
            body = _build_valid_body(ep, overrides={field: long_val})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 超长(10000字符)",
                priority="P2",
                scenario="extreme_long",
                body=body,
                assertions=[
                    {"type": "status_code", "expected": 200, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{field} 超长字符串不应导致 5xx 服务端错误。",
            ))

        # SQL 注入
        sql_payload = _SQL_INJECTION_PAYLOADS[0]
        body = _build_valid_body(ep, overrides={field: sql_payload})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} SQL注入",
            priority="P1",
            scenario="extreme_sql",
            body=body,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 包含 SQL 注入片段时应被安全过滤或拒绝，不应 5xx。",
        ))

        # XSS
        xss_payload = _XSS_PAYLOADS[0]
        body = _build_valid_body(ep, overrides={field: xss_payload})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} XSS注入",
            priority="P2",
            scenario="extreme_xss",
            body=body,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 包含 XSS 片段时应被安全过滤或拒绝，不应 5xx。",
        ))

        # 特殊字符
        special_val = _SPECIAL_CHARACTERS[3]  # 标点符号集
        body = _build_valid_body(ep, overrides={field: special_val})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 特殊字符",
            priority="P2",
            scenario="extreme_special_chars",
            body=body,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 含特殊字符时应正常处理，不应 5xx。",
        ))

    return cases


# ═══════════════════════════════════════════════════════
# Query 参数校验
# ═══════════════════════════════════════════════════════

def _build_query_required_cases(ep: dict, query_params: list) -> list[dict]:
    """为必填 query 参数生成缺失/空值/类型错误用例。"""
    cases = []
    required = [q for q in query_params if q.get("required")]
    for q in required:
        name = q.get("name", "")
        # Missing required query param
        cases.append(_make_case(
            ep,
            purpose=f"{name} 缺失应返回参数错误", field=name,
            priority="P1", scenario="query_required",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"缺少必填 query 参数 {name} 时应返回 4xx。",
        ))
    return cases


def _build_query_type_cases(ep: dict, query_params: list) -> list[dict]:
    """为 query 参数生成类型错误用例。"""
    cases = []
    for q in query_params[:3]:  # limit to first 3
        name = q.get("name", "")
        ptype = q.get("type", "string")
        if ptype in ("integer", "number"):
            cases.append(_make_case(
                ep,
                purpose=f"{name} 类型错误应返回参数错误", field=name,
                priority="P2", scenario="query_type",
                body=_build_valid_body(ep),
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{name} 传入非{ptype}类型时应返回 4xx。",
            ))
    return cases


def _build_query_injection_cases(ep: dict, query_params: list) -> list[dict]:
    """为 query 参数生成 SQL/XSS 注入用例。"""
    cases = []
    for q in query_params[:2]:
        name = q.get("name", "")
        cases.append(_make_case(
            ep,
            purpose=f"{name} 包含SQL注入片段应被拦截或安全处理", field=name,
            priority="P1", scenario="query_injection",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{name} 包含 SQL 注入时应被安全处理，不应 5xx。",
        ))
    return cases


# ═══════════════════════════════════════════════════════
# Path 参数校验
# ═══════════════════════════════════════════════════════

def _build_path_param_cases(ep: dict, path_params: list) -> list[dict]:
    """为 path 参数生成校验用例。"""
    cases = []
    for p in path_params[:3]:
        name = p.get("name", "")
        ptype = p.get("type", "string")
        # Type mismatch for numeric path params
        if ptype in ("integer", "number"):
            cases.append(_make_case(
                ep,
                purpose=f"{name} 类型错误应返回 404 或参数错误", field=name,
                priority="P2", scenario="path_invalid",
                body=_build_valid_body(ep),
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"Path 参数 {name} 类型错误时应返回 4xx。",
            ))
    return cases


# ═══════════════════════════════════════════════════════
# Header 参数校验
# ═══════════════════════════════════════════════════════

def _build_header_param_cases(ep: dict, header_params: list) -> list[dict]:
    """为 header 参数生成校验用例。"""
    cases = []
    required_headers = [h for h in header_params if h.get("required")]
    for h in required_headers[:2]:
        name = h.get("name", "")
        cases.append(_make_case(
            ep,
            purpose=f"缺少 {name} 请求头应返回参数错误", field=name,
            priority="P1", scenario="header_missing",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"缺少必填 header {name} 时应返回 4xx。",
        ))
    return cases


# ═══════════════════════════════════════════════════════
# 安全注入 (SQL/XSS/Path Traversal)
# ═══════════════════════════════════════════════════════

def _build_security_cases(ep: dict, properties: dict) -> list[dict]:
    """为 string 字段生成 SQL/XSS/Path Traversal 安全用例。"""
    method = ep.get("method", "GET").upper()
    cases = []
    string_fields = [f for f, p in properties.items() if p.get("type") == "string"]

    for field in string_fields[:2]:
        # SQL injection
        cases.append(_make_case(
            ep,
            purpose=f"{field} 包含SQL注入片段应被拦截或安全处理", field=field,
            priority="P1", scenario="security_sql",
            body=_build_valid_body(ep, overrides={field: "' OR '1'='1' --"}),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 含 SQL 注入时不应 5xx。",
        ))
        # XSS
        cases.append(_make_case(
            ep,
            purpose=f"{field} 包含脚本片段应被过滤或拒绝", field=field,
            priority="P2", scenario="security_xss",
            body=_build_valid_body(ep, overrides={field: "<script>alert(1)</script>"}),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 含 XSS 时不应 5xx。",
        ))

    return cases


# ═══════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════

# ── 场景类型中文标签 ──
_SCENARIO_LABELS: dict[str, str] = {
    "positive": "正向",
    "required_missing": "必填",
    "required_null": "必填校验",
    "required_empty": "必填校验",
    "type_error": "类型校验",
    "enum_invalid": "枚举校验",
    "boundary_min": "边界值",
    "boundary_max": "边界值",
    "boundary_valid": "边界值",
    "format_error": "格式校验",
    "idempotency": "幂等",
    "extreme_long": "极限",
    "extreme_sql": "安全",
    "extreme_xss": "安全",
    "extreme_special_chars": "极限",
    "auth_missing": "鉴权",
    "query_required": "Query必填",
    "query_type": "Query类型",
    "query_injection": "Query安全",
    "path_invalid": "Path校验",
    "header_missing": "Header缺失",
    "header_type": "Header类型",
    "security_sql": "SQL注入",
    "security_xss": "XSS",
    "security_path_traversal": "路径遍历",
}


def _scenario_label(scenario: str) -> str:
    return _SCENARIO_LABELS.get(scenario, scenario)


def _make_case(
    ep: dict,
    *,
    title: str = "",
    purpose: str = "",
    field: str = "",
    priority: str,
    scenario: str,
    body: dict | str,
    assertions: list[dict],
    expected: str,
    extra_headers: dict | None = None,
    strip_auth: bool = False,
) -> dict:
    """构造统一的用例 dict。标题自动使用 【场景】summary - field - purpose 格式。"""
    method = ep.get("method", "GET").upper()
    path = ep.get("path", "")
    service = ep.get("service_name", "")
    module = ep.get("module", "")
    summary = ep.get("summary") or ep.get("path", "")
    scenario_label = _scenario_label(scenario)

    # Auto-format title: 【Scenario】summary - field - purpose
    if purpose and field:
        formatted_title = f"【{scenario_label}】{summary} - {field} - {purpose}"
    elif purpose:
        formatted_title = f"【{scenario_label}】{summary} - {purpose}"
    elif title:
        formatted_title = f"【{scenario_label}】{title}"
    else:
        formatted_title = f"【{scenario_label}】{summary}"

    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    body_str = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)

    # 对于 GET/HEAD/DELETE 等请求，body 通常为空
    if method in ("GET", "HEAD"):
        body_str = ""

    return {
        "title": formatted_title,
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
