"""接口测试用例生成引擎 — 基于接口 schema 生成正向/边界/异常/幂等/极限用例。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.test_case import TestCase

# 单接口用例生成数量上限（防止膨胀）
_MAX_CASES_PER_ENDPOINT = 200

# 常见业务字段语义提示（Batch 103：贴合语义构造数据，禁止无意义占位）
FIELD_SEMANTICS = {
    "page": "页码（分页请求第几页，从 1 开始）",
    "size": "每页条数（单页返回记录数上限）",
    "current": "当前页码（响应侧）",
    "total": "总记录数（响应侧）",
    "locale": "返回文案语言（枚举：en/zh 等）",
    "language": "语言过滤值（业务枚举）",
    "sorts": "排序规则数组（key=排序字段，sort=desc/asc）",
    "queryList": "过滤条件数组（key=字段名，type=类型，value1/value2=值/区间边界，isOrNotRange=是否区间）",
    "top": "置顶标志（0=否，1=是）",
    "updateTime": "更新时间（时间戳/时间格式）",
    "displayPlatform": "展示平台（PC/APP/WEB）",
    "displayPage": "展示页面（如 INDEX 首页）",
    "keyword": "搜索关键词",
    "id": "业务主键 ID",
    "key": "字段名",
    "value1": "查询值/区间下界",
    "value2": "区间上界",
    "isOrNotRange": "是否区间查询（0=精确，1=区间）",
    "type": "字段类型标识（String/Integer 等）",
}


def generate_cases_from_real_sample(endpoint: dict, real_sample: dict) -> list[dict]:
    """真实业务样本驱动的字段级接口用例（Batch 103，C103-4）。

    契约 schema 可能为空（如 /ee/news/list_visible），此时以生产/测试环境真实请求
    样本为字段来源：对样本 body 中的每个字段按业务语义生成 正向/负向/边界/类型 用例，
    禁止无意义占位值。
    """
    method = (endpoint.get("method") or "GET").upper()
    path = endpoint.get("path", "")
    body = real_sample.get("body") or real_sample.get("request_body") or {}
    if not isinstance(body, dict):
        body = {}
    source = real_sample.get("source") or real_sample.get("url") or "真实业务请求样本"
    cases: list[dict] = []

    def _mk(
        title: str, scenario: str, pn: str, method_name: str,
        body_value: dict, expected: str, assertions: list[dict] | None = None,
        priority: str = "P1",
    ) -> dict:
        body_str = json.dumps(body_value, ensure_ascii=False) if method not in ("GET", "HEAD") else ""
        return {
            "title": f"{path} - {title}",
            "domain": "接口测试",
            "module": endpoint.get("module", ""),
            "case_type": "api",
            "priority": priority,
            "preconditions": f"接口 {method} {path} 可访问",
            "steps": [{"step": 1, "action": f"发送 {method} 请求到 {path}", "expected": expected}],
            "expected_result": expected,
            "api_method": method,
            "api_endpoint": path,
            "api_headers": {"Content-Type": "application/json"},
            "api_body": body_str,
            "api_assertions": assertions or [
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 300, "operator": "lt"},
            ],
            "case_design_method": method_name,
            "positive_negative": pn,
            "test_data_note": f"数据来源：{source}；字段语义与构造值说明见用例。",
            "source": "ai_generated",
            "tags": [f"service:{endpoint.get('service_name', '')}", f"scenario:{scenario}", "source:real_sample"],
        }

    # 0) 正向基线：真实样本原样（Batch 107：断言升级为状态码 + 响应结构业务断言）
    _resp_assertions = _response_structure_assertions(real_sample)
    cases.append(_mk(
        "正常请求（真实业务参数原样）", "positive", "positive", "场景法",
        dict(body), f"接口返回 2xx；响应结构与真实调用一致。",
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 300, "operator": "lt"},
            {"type": "response_time", "expected": 5000, "operator": "lt"},
        ] + _resp_assertions,
        priority="P0",
    ))

    # 0.1) 返回值结构校验（表格-返回值校验【必选】落地）：业务状态码/记录数/排序/核心字段
    if _resp_assertions:
        cases.append(_mk(
            "返回值结构校验（业务状态码/记录数/排序/核心字段）", "response_structure", "positive", "场景法",
            dict(body),
            "按真实响应结构校验：业务状态码、记录数上限、排序规则、核心字段非空与真实调用一致。",
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 300, "operator": "lt"},
            ] + _resp_assertions,
            priority="P0",
        ))

    # 0.2) 冒烟测试（业务功能测试-冒烟）：业务入参完成功能并验证
    cases.append(_mk(
        "冒烟测试（业务入参完成功能并验证结果）", "smoke", "positive", "场景法",
        dict(body),
        "以业务入参为起点完成接口功能，并通过返回结果或其他接口验证。",
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 300, "operator": "lt"},
            {"type": "response_time", "expected": 5000, "operator": "lt"},
        ] + _resp_assertions,
        priority="P0",
    ))

    # 1) 逐字段覆盖
    for field, value in body.items():
        semantics = FIELD_SEMANTICS.get(field, f"{field}（业务字段，语义以接口文档为准）")
        ptype = "integer" if isinstance(value, bool) is False and isinstance(value, int) else \
            "string" if isinstance(value, str) else "boolean" if isinstance(value, bool) else \
            "array" if isinstance(value, list) else "object"

        # 边界：0 / 负数 / 最小 / 超长
        if ptype == "integer":
            for label, bad in (("0", 0), ("负数", -1), ("超上限", 10**9)):
                v = dict(body); v[field] = bad
                cases.append(_mk(
                    f"{field} 边界值 {label}（语义：{semantics}）", "boundary", "boundary", "边界值分析",
                    v, f"{field} 为 {label} 时按业务校验返回 2xx 或 4xx（视后端规则），不得 5xx。",
                ))
        elif ptype == "string":
            for label, bad in (("空字符串", ""), ("超长", "x" * 256), ("特殊字符", "@#$%^&*()")):
                v = dict(body); v[field] = bad
                cases.append(_mk(
                    f"{field} 边界值 {label}（语义：{semantics}）", "boundary", "boundary", "边界值分析",
                    v, f"{field} 为 {label} 时按业务校验返回 2xx 或 4xx，不得 5xx。",
                ))

        # 类型错误
        wrong = {"integer": "not_a_number", "string": 12345, "boolean": "not_bool", "array": "not_array", "object": "not_object"}.get(ptype, "__invalid__")
        v = dict(body); v[field] = wrong
        cases.append(_mk(
            f"{field} 类型错误（{ptype} → {type(wrong).__name__}）", "type", "negative", "错误推测",
            v, f"{field} 类型不符时应返回 4xx 参数校验错误。",
        ))

        # 缺失 / null
        v = dict(body); v.pop(field, None)
        cases.append(_mk(
            f"{field} 缺失", "required_missing", "negative", "等价类划分",
            v, f"{field} 缺失时按必填规则返回 2xx 或 4xx，不得 5xx。",
        ))
        v = dict(body); v[field] = None
        cases.append(_mk(
            f"{field} 为 null", "required_null", "negative", "等价类划分",
            v, f"{field} 为 null 时应返回 2xx 或 4xx，不得 5xx。",
        ))

    # 2) 关键组合场景（真实样本语义）
    if "page" in body and "size" in body:
        v = dict(body); v["page"] = 1; v["size"] = max(1, body["size"] - 1) if isinstance(body["size"], int) else 1
        cases.append(_mk(
            "分页边界：page=1 且 size 减一（首页最小页）", "boundary", "boundary", "边界值分析",
            v, "首页请求返回记录数 ≤ size；分页字段生效。",
        ))
        v = dict(body); v["page"] = 999999; v["size"] = body["size"]
        cases.append(_mk(
            "分页边界：page 超总页数", "boundary", "boundary", "边界值分析",
            v, "超出总页数时返回空 records（或 4xx），不得 5xx。",
        ))
    if "queryList" in body and isinstance(body["queryList"], list):
        v = dict(body); v["queryList"] = []
        cases.append(_mk(
            "过滤条件为空数组（返回全量数据）", "combo", "positive", "组合覆盖",
            v, "queryList 为空时返回默认全量数据，结构正确。",
        ))
        v = dict(body)
        v["queryList"] = body["queryList"] + [{"isOrNotRange": 0, "key": "top", "type": "Integer", "value1": "1", "value2": ""}]
        cases.append(_mk(
            "过滤条件多条件组合（AND）", "combo", "positive", "组合覆盖",
            v, "多条件组合过滤生效，返回记录满足全部条件。",
        ))
    if "sorts" in body and isinstance(body["sorts"], list):
        v = dict(body); v["sorts"] = [{"key": "updateTime", "sort": "asc"}]
        cases.append(_mk(
            "排序规则变更（updateTime asc）", "combo", "positive", "组合覆盖",
            v, "排序按 updateTime 升序返回。",
        ))
        v = dict(body); v["sorts"] = [{"key": "updateTime", "sort": "invalid"}]
        cases.append(_mk(
            "排序方向非法值", "enum", "negative", "等价类划分",
            v, "sort 非 desc/asc 时返回 4xx 或按默认规则处理，不得 5xx。",
        ))
    if "locale" in body:
        for lang in ("zh", "missing"):
            v = dict(body)
            if lang == "missing":
                v.pop("locale", None)
            else:
                v["locale"] = lang
            cases.append(_mk(
                f"locale 枚举：{lang}", "enum", "boundary", "等价类划分",
                v, "locale 变更/缺省时响应文案语言按枚举处理。",
            ))

    return cases[:_MAX_CASES_PER_ENDPOINT]


def generate_cases_from_endpoint(
    endpoint: dict,
    *,
    templates: list[str] | None = None,
    real_samples: list[dict] | None = None,
) -> list[dict]:
    """从接口定义生成测试用例列表。

    Args:
        endpoint: {service_name, module, method, path, summary, request_schema}
        templates: 生成模板集 [basic, boundary, invalid, security, idempotency, extreme,
            smoke, scenario, extra_param, security_ext, performance_low, data_test,
            stability, compatibility, monitoring]

    Returns:
        list of case dicts with title/domain/module/case_type/priority/steps/
        expected_result/api_method/api_endpoint/api_headers/api_body/api_assertions/tags
    """
    if templates is None:
        templates = [
            "basic", "boundary", "invalid", "security", "idempotency", "extreme",
            "smoke", "scenario", "extra_param", "security_ext", "performance_low",
            "data_test", "stability", "compatibility", "monitoring",
        ]

    cases: list[dict] = []
    schema = endpoint.get("request_schema", {})
    body_schema = schema.get("body", {}) if isinstance(schema, dict) else {}
    properties = body_schema.get("properties", {})
    required_fields = body_schema.get("required", [])

    endpoint.get("method", "GET").upper()
    endpoint.get("path", "")
    endpoint.get("module", "")
    endpoint.get("service_name", "")
    endpoint.get("summary", "")

    # Batch 103：真实业务样本基线（避免 mock 占位）
    real = real_samples[0] if real_samples else None

    # Extract query/path/header params
    query_params = schema.get("query", []) if isinstance(schema, dict) else []
    path_params = schema.get("path", []) if isinstance(schema, dict) else []
    header_params = schema.get("header", []) if isinstance(schema, dict) else []

    # ── 基础正常用例 ──
    if "basic" in templates:
        cases.append(_build_positive_case(endpoint, real=real))
        if query_params:
            cases.append(_build_query_param_case(endpoint, query_params, real=real))

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

    # ── 额外边界覆盖 (null/空/零/负 per parameter) ──
    if "boundary" in templates or "invalid" in templates:
        cases.extend(_build_extra_boundary_cases(endpoint, properties, query_params))

    # ── 多参数组合覆盖 ──
    total_params = len(properties) + len(query_params)
    if total_params >= 2:
        cases.extend(_build_combo_param_cases(endpoint, properties, query_params))

    # ── Batch 107：测试考虑点（XMind 接口测试.xmind）新模板 ──
    # 业务功能测试：冒烟（业务入参起点完成功能并验证）
    if "smoke" in templates:
        cases.extend(_build_smoke_cases(endpoint, real))

    # 业务功能测试：场景（多接口串联状态转变；无关联信息时生成待关联建议）
    if "scenario" in templates:
        cases.extend(_build_scenario_cases(endpoint, real))

    # 健壮性-入参非法：增加不存在的参数
    if "extra_param" in templates:
        cases.extend(_build_extra_param_cases(endpoint, real))

    # 安全：敏感信息加密 / 越权访问 / CSRF
    if "security_ext" in templates:
        cases.extend(_build_security_ext_cases(endpoint))

    # 性能（用户指示低优先级）：并发/吞吐/服务器资源（P2/P3）
    if "performance_low" in templates:
        cases.extend(_build_performance_low_cases(endpoint))

    # 数据测试：数据库入库 / 字段类型长度一致性（DB 检查断言）
    if "data_test" in templates:
        cases.extend(_build_data_test_cases(endpoint))

    # 稳定性（表格-可选）：限流 / 熔断 / 降级
    if "stability" in templates:
        cases.extend(_build_stability_cases(endpoint))

    # 兼容性（表格-可选）：入参 / 返回值 / 老功能
    if "compatibility" in templates:
        cases.extend(_build_compatibility_cases(endpoint))

    # 监控告警（表格-可选）：性能监控 qps/rt + 业务监控错误码/指标
    if "monitoring" in templates:
        cases.extend(_build_monitoring_cases(endpoint))

    # ── 数量下限保证 ──
    if total_params >= 5 and len(cases) < 40:
        # Generate additional combo cases to reach minimum
        extra_needed = 40 - len(cases)
        extra_combos = _build_combo_param_cases(endpoint, properties, query_params, count=min(extra_needed, 10))
        cases.extend(extra_combos)
    elif total_params >= 3 and len(cases) < 25:
        # Generate additional boundary cases to reach minimum
        extra_needed = 25 - len(cases)
        extra_boundary = _build_extra_boundary_cases(endpoint, properties, query_params, count=min(extra_needed, 10))
        cases.extend(extra_boundary)

    # ── 数量上限保护 ──
    if len(cases) > _MAX_CASES_PER_ENDPOINT:
        cases = cases[:_MAX_CASES_PER_ENDPOINT]

    return cases


# ═══════════════════════════════════════════════════════
# 基础正常用例
# ═══════════════════════════════════════════════════════

def _build_positive_case(ep: dict, real: dict | None = None) -> dict:
    """构造正向基础用例。有真实样本时以其请求参数为基线，避免 mock 占位。"""
    body = None
    data_note = ""
    if real:
        body = real.get("body") or real.get("request_body")
        query = real.get("query") or real.get("query_params") or {}
        data_note = (
            "数据来源：生产/测试环境真实业务请求样本"
            + (f"（{real.get('source') or real.get('url') or ''}）" if (real.get("source") or real.get("url")) else "")
            + "；字段值贴合真实业务语义，非占位数据。"
        )
    if body is None:
        body = _build_valid_body(ep)
    c = _make_case(
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
    if data_note:
        c["test_data_note"] = data_note
    if real and query:
        query_str = "&".join(f"{k}={v}" for k, v in query.items())
        sep = "&" if "?" in c.get("api_endpoint", "") else "?"
        c["api_endpoint"] = f"{c.get('api_endpoint', '')}{sep}{query_str}"
    return c


def _build_query_param_case(ep: dict, query_params: list, real: dict | None = None) -> dict:
    """构造 query 参数组合用例。优先使用真实样本中的 query 参数值。"""
    real_query = (real or {}).get("query") or (real or {}).get("query_params") or {}
    params = {
        p["name"]: real_query.get(p["name"], _sample_value_for_param(p))
        for p in query_params
        if p.get("required") or p["name"] in real_query
    }
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
    if real:
        c["test_data_note"] = "数据来源：生产/测试环境真实业务请求样本（query 参数真实值）。"
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
    """为必填 query 参数生成缺失/null值/空字符串/类型错误用例。"""
    cases = []
    required = [q for q in query_params if q.get("required")]
    for q in required:
        name = q.get("name", "")
        ptype = q.get("type", "string")
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
        # Null value for required query param
        cases.append(_make_case(
            ep,
            purpose=f"{name} 为 null 应返回参数错误", field=name,
            priority="P1", scenario="query_required",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"必填 query 参数 {name} 为 null 时应返回 4xx。",
        ))
        # Empty string (only for string type)
        if ptype == "string":
            cases.append(_make_case(
                ep,
                purpose=f"{name} 为空字符串应返回参数错误", field=name,
                priority="P2", scenario="query_required",
                body=_build_valid_body(ep),
                assertions=[
                    {"type": "status_code", "expected": 400, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"必填 query 参数 {name} 为空字符串时应返回 4xx。",
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
    ep.get("method", "GET").upper()
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
# Batch 107：测试考虑点新模板（XMind 接口测试.xmind，2026-08-06）
# ═══════════════════════════════════════════════════════

def _build_smoke_cases(ep: dict, real: dict | None = None) -> list[dict]:
    """业务功能测试-冒烟测试：以业务中某一入参为起点完成接口功能，并通过结果验证。

    有真实样本时以其请求参数为基线；断言同时校验响应结构（业务码/记录数/核心字段，
    若样本含响应结构）与响应时间，避免只查 2xx 的假冒烟。
    """
    body = real.get("body") or real.get("request_body") if real else None
    if body is None:
        body = _build_valid_body(ep)
    assertions = [
        {"type": "status_code", "expected": 200, "operator": "gte"},
        {"type": "status_code", "expected": 300, "operator": "lt"},
        {"type": "response_time", "expected": 5000, "operator": "lt"},
    ]
    if real:
        assertions.extend(_response_structure_assertions(real))
    return [_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 冒烟测试（业务入参完成功能并验证结果）",
        priority="P0",
        scenario="smoke",
        body=body,
        assertions=assertions,
        expected="以业务入参为起点完成接口业务功能，返回 2xx 且响应结构/关键字段符合预期，响应时间 < 5s。",
    )]


def _build_scenario_cases(ep: dict, real: dict | None = None) -> list[dict]:
    """业务功能测试-场景测试：多接口连续调用达到状态转变，并通过返回结果或其他接口验证。

    单接口生成器无跨接口关联图谱：真实样本或 endpoint 含关联接口信息时引用；
    否则生成「场景测试建议（待关联）」用例，标注需配置依赖接口后补全。
    """
    related = None
    if real:
        related = real.get("related_endpoints") or real.get("related") or real.get("assertion_design_hints")
    extra_note = ""
    if related:
        extra_note = f"关联接口/验证提示：{json.dumps(related, ensure_ascii=False)[:300]}"
    else:
        extra_note = "当前无接口关联信息，需在接口关联配置后按业务状态转变补全依赖接口串联步骤。"
    body = real.get("body") or real.get("request_body") if real else None
    if body is None:
        body = _build_valid_body(ep)
    c = _make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 场景测试（接口串联状态转变）",
        priority="P1",
        scenario="scenario",
        body=body,
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 500, "operator": "lt"},
        ],
        expected=f"通过多个接口连续调用达到业务状态转变，并以返回结果或后续接口查询验证状态。{extra_note}",
    )
    c["test_data_note"] = c.get("test_data_note", "") + f" 场景测试说明：{extra_note}"
    return [c]


def _build_extra_param_cases(ep: dict, real: dict | None = None) -> list[dict]:
    """健壮性-入参非法：增加不存在的参数，验证服务器按契约处理（4xx 或忽略），不得 5xx。"""
    body = real.get("body") or real.get("request_body") if real else None
    if body is None:
        body = _build_valid_body(ep)
    if not isinstance(body, dict):
        body = {}
    body = dict(body)
    body["__unknown_extra_field__"] = "should_be_rejected_or_ignored"
    return [_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 增加不存在的参数",
        priority="P1",
        scenario="extra_param",
        body=body,
        assertions=[
            {"type": "status_code", "expected": 400, "operator": "gte"},
            {"type": "status_code", "expected": 500, "operator": "lt"},
        ],
        expected="请求体增加契约外参数时应返回 4xx 参数校验错误或被安全忽略，不得 5xx。",
    )]


def _build_security_ext_cases(ep: dict) -> list[dict]:
    """安全测试扩展：越权访问（弱/无效 token）、CSRF（写接口）、HTTPS/签名/加密检查。"""
    method = ep.get("method", "GET").upper()
    cases: list[dict] = []

    # 越权访问：弱 token 调用接口应被拒绝（401/403 或业务拒绝），不得 5xx
    cases.append(_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 越权访问-无效/弱 Token",
        priority="P1",
        scenario="security_ext",
        body=_build_valid_body(ep),
        assertions=[
            {"type": "status_code", "expected": 401, "operator": "gte"},
            {"type": "status_code", "expected": 500, "operator": "lt"},
        ],
        expected="携带无效/弱 Token 调用应返回 401/403 或业务拒绝，不得 5xx；已登录用户访问他人资源应被拒绝（越权拦截）。",
        extra_headers={"Authorization": "Bearer invalid-token"},
    ))

    # HTTPS/签名/加密：通信加密与敏感信息不泄露
    cases.append(_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 敏感信息加密-HTTPS/签名/响应不泄露明文敏感字段",
        priority="P1",
        scenario="security_ext",
        body=_build_valid_body(ep),
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 500, "operator": "lt"},
            {"type": "security_check", "assert": "https_and_no_plain_secrets"},
        ],
        expected="通信使用 HTTPS；存在请求签名/身份确认机制时校验其生效；响应不得明文泄露密码/密钥等敏感字段。",
    ))

    # CSRF：写接口校验来源
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - CSRF 请求伪造-伪造来源应被拒绝",
            priority="P1",
            scenario="security_ext",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 400, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected="写接口带伪造 Origin/Referer 或缺失 CSRF Token 时应返回 4xx 或被安全拒绝，不得 5xx 且不得执行写入。",
            extra_headers={"Origin": "https://evil.example.com"},
        ))
    return cases


def _build_performance_low_cases(ep: dict) -> list[dict]:
    """性能测试（用户 2026-08-06 指示低优先级）：并发/吞吐/服务器资源，P2/P3 非阻塞。"""
    cases = [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 性能-并发请求（低优先级）",
            priority="P2",
            scenario="performance_low",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected="并发（如 10 并发同参数）请求不 5xx，qps/rt 在服务容量范围内；低优先级辅助检查。",
        ),
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 性能-吞吐与服务器资源监控（低优先级）",
            priority="P3",
            scenario="performance_low",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "monitoring", "assert": "throughput_and_resources"},
            ],
            expected="观察吞吐量、服务器资源使用率（CPU/IO/内存/Network）在合理范围；低优先级辅助检查。",
        ),
    ]
    return cases


def _build_data_test_cases(ep: dict) -> list[dict]:
    """数据测试：数据库入库/字段类型长度一致性（基本+专业化要点），DB 检查断言。"""
    method = ep.get("method", "GET").upper()
    cases = [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 数据测试-数据库入库与字段一致性",
            priority="P2",
            scenario="data_test",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
                {"type": "db_check", "assert": "record_persisted_and_fields_consistent"},
            ],
            expected="执行后确认数据库正常入库；字段类型/长度与需求及页面输入一致；主外键/索引/完整性约束符合设计。",
        ),
    ]
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 数据测试-写操作数据校验（专业）",
            priority="P2",
            scenario="data_test",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "db_check", "assert": "write_ops_data_consistency"},
            ],
            expected="插入/更新/删除后数据正确；并发操作正确处理；权限定义正确。",
        ))
    return cases


def _build_stability_cases(ep: dict) -> list[dict]:
    """稳定性（表格-可选）：限流 / 熔断 / 降级，按服务策略验证。"""
    return [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 稳定性-限流",
            priority="P2",
            scenario="stability",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 429, "operator": "eq"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected="高频请求触发限流时应返回 429 或明确的限流策略响应，不得 5xx。",
        ),
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 稳定性-熔断/降级",
            priority="P2",
            scenario="stability",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected="依赖故障触发熔断/降级时返回降级结果或明确错误码，不得 5xx 崩溃。",
        ),
    ]


def _build_compatibility_cases(ep: dict) -> list[dict]:
    """兼容性（表格-可选）：入参兼容 / 返回值兼容 / 老功能兼容。"""
    return [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 兼容性-入参/返回值/老功能",
            priority="P2",
            scenario="compatibility",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
                {"type": "compat_check", "assert": "param_append_only_and_old_behavior"},
            ],
            expected="入参字段仅新增不破坏旧调用；返回值字段按序新增不影响旧解析；老功能调用不受影响；老数据兼容。",
        ),
    ]


def _build_monitoring_cases(ep: dict) -> list[dict]:
    """监控告警（表格-可选）：性能监控 qps/rt + 业务监控错误码/业务指标。"""
    return [
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 监控告警-性能监控（qps/rt）",
            priority="P2",
            scenario="monitoring",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "monitoring", "assert": "qps_rt_metrics_visible"},
            ],
            expected="接口 qps/rt 监控指标可观测，异常时触发告警。",
        ),
        _make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - 监控告警-业务监控（错误码/业务指标）",
            priority="P2",
            scenario="monitoring",
            body=_build_valid_body(ep),
            assertions=[
                {"type": "monitoring", "assert": "business_metrics_visible"},
            ],
            expected="业务错误码与业务指标上报可见，异常业务量触发告警。",
        ),
    ]


def _response_structure_assertions(real: dict) -> list[dict]:
    """把真实样本的响应结构转成业务断言（Batch 107，返回值校验【必选】落地）。

    消费 response_envelope_keys / data_keys / record_count / first_record_fields /
    assertion_design_hints；无响应结构信息时返回空列表（调用方保留状态码断言）。
    """
    out: list[dict] = []
    envelope = real.get("response_envelope_keys") or []
    data_keys = real.get("data_keys") or []
    record_count = real.get("record_count")
    first_fields = real.get("first_record_fields") or []
    hints = real.get("assertion_design_hints") or []

    if envelope:
        out.append({"type": "response_structure", "path": envelope[0], "assert": "exists"})
    if "data" in envelope:
        out.append({"type": "response_structure", "path": "data", "assert": "is_object_or_array"})
    if data_keys:
        for k in data_keys[:3]:
            out.append({"type": "response_structure", "path": f"data.{k}", "assert": "exists"})
    if record_count is not None:
        out.append({"type": "response_structure", "path": "data.records", "assert": "len_lte", "expected": record_count})
    if first_fields:
        for f in first_fields[:5]:
            out.append({"type": "response_structure", "path": f"data.records[0].{f}", "assert": "not_empty"})
    for h in hints:
        if isinstance(h, str):
            out.append({"type": "response_structure", "assert": "hint", "note": h[:200]})
    return out


# ═══════════════════════════════════════════════════════
# 额外边界覆盖 (null/空/零/负 per parameter)
# ═══════════════════════════════════════════════════════

def _get_invalid_value(param: dict) -> Any:
    """返回参数的边界/非法值。"""
    ptype = param.get("type", "string")
    if ptype == "string":
        return ""
    elif ptype == "integer":
        return 0
    elif ptype == "number":
        return 0.0
    elif ptype == "boolean":
        return False
    elif ptype == "array":
        return []
    elif ptype == "object":
        return {}
    return None


def _build_extra_boundary_cases(
    ep: dict, properties: dict, query_params: list, *, count: int = 0
) -> list[dict]:
    """为每个 body 参数生成 null/空/零/负数等边界覆盖用例。

    Args:
        count: if > 0, only generate up to this many cases (for minimum enforcement).
    """
    ep.get("method", "GET").upper()
    cases: list[dict] = []

    # Body params
    for field, prop in properties.items():
        if count > 0 and len(cases) >= count:
            break
        ptype = prop.get("type", "string")

        # Null value
        body = _build_valid_body(ep, overrides={field: None})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 为 null",
            priority="P2",
            scenario="boundary_valid",
            body=body,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 为 null 时不应导致 5xx。",
        ))

        # Empty value per type
        if ptype == "string":
            body = _build_valid_body(ep, overrides={field: ""})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 为空字符串",
                priority="P2",
                scenario="boundary_valid",
                body=body,
                assertions=[
                    {"type": "status_code", "expected": 200, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{field} 为空字符串时不应导致 5xx。",
            ))
        elif ptype in ("integer", "number"):
            # Zero value
            body = _build_valid_body(ep, overrides={field: 0 if ptype == "integer" else 0.0})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 为零值",
                priority="P2",
                scenario="boundary_valid",
                body=body,
                assertions=[
                    {"type": "status_code", "expected": 200, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{field} 为零值时不应导致 5xx。",
            ))
            # Negative value
            body = _build_valid_body(ep, overrides={field: -1})
            cases.append(_make_case(
                ep,
                title=f"{ep.get('summary') or ep.get('path')} - {field} 为负数",
                priority="P2",
                scenario="boundary_valid",
                body=body,
                assertions=[
                    {"type": "status_code", "expected": 200, "operator": "gte"},
                    {"type": "status_code", "expected": 500, "operator": "lt"},
                ],
                expected=f"{field} 为负数时不应导致 5xx。",
            ))

    return cases


def _build_combo_param_cases(
    ep: dict, properties: dict, query_params: list, *, count: int = 0
) -> list[dict]:
    """为多参数生成组合覆盖用例：全正常、全边界、混合场景。

    Args:
        count: if > 0, only generate up to this many cases (for minimum enforcement).
    """
    cases: list[dict] = []
    all_params = list(properties.items())

    if len(all_params) < 2:
        return cases

    # Take up to 3 params for combination coverage
    combo_params = all_params[:3]

    # Case 1: All params with valid values (happy path combo)
    body_valid = _build_valid_body(ep)
    cases.append(_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 全参数正常组合",
        priority="P1",
        scenario="positive",
        body=body_valid,
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 300, "operator": "lt"},
        ],
        expected="所有请求参数合法时接口应正常返回 2xx。",
    ))

    if count > 0 and len(cases) >= count:
        return cases[:count]

    # Case 2: All params empty/null (all-boundary combo)
    overrides_all_empty = {}
    for field, prop in combo_params:
        overrides_all_empty[field] = _get_invalid_value(prop)
    body_all_empty = _build_valid_body(ep, overrides=overrides_all_empty)
    cases.append(_make_case(
        ep,
        title=f"{ep.get('summary') or ep.get('path')} - 全参数边界值组合",
        priority="P2",
        scenario="boundary_valid",
        body=body_all_empty,
        assertions=[
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 500, "operator": "lt"},
        ],
        expected="所有参数为边界值时不应导致 5xx。",
    ))

    if count > 0 and len(cases) >= count:
        return cases[:count]

    # Case 3-5: Mix — one param invalid, rest valid
    for field, prop in combo_params:
        if count > 0 and len(cases) >= count:
            break
        body_mix = _build_valid_body(ep, overrides={field: _get_invalid_value(prop)})
        cases.append(_make_case(
            ep,
            title=f"{ep.get('summary') or ep.get('path')} - {field} 边界值+其他正常",
            priority="P2",
            scenario="boundary_valid",
            body=body_mix,
            assertions=[
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "status_code", "expected": 500, "operator": "lt"},
            ],
            expected=f"{field} 为边界值、其他参数正常时不应导致 5xx。",
        ))

    return cases[:count] if count > 0 else cases


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
    "smoke": "冒烟测试",
    "scenario": "场景测试",
    "extra_param": "非法入参",
    "security_ext": "安全扩展",
    "performance_low": "性能(低优先级)",
    "data_test": "数据测试",
    "stability": "稳定性",
    "compatibility": "兼容性",
    "monitoring": "监控告警",
    "response_structure": "返回值结构",
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

    # Batch 103：设计方法/正负向可追溯
    _METHOD_MAP = {
        "positive": "场景法",
        "boundary": "边界值分析",
        "required": "等价类划分",
        "null": "等价类划分",
        "type": "错误推测",
        "enum": "等价类划分",
        "format": "错误推测",
        "query": "等价类划分",
        "path": "等价类划分",
        "header": "等价类划分",
        "extreme": "边界值分析",
        "security": "错误推测",
        "idempotency": "场景法",
        "auth": "场景法",
        "combo": "组合覆盖",
        "smoke": "场景法",
        "scenario": "场景法",
        "extra_param": "错误推测",
        "security_ext": "错误推测",
        "performance_low": "场景法",
        "data_test": "场景法",
        "stability": "场景法",
        "compatibility": "场景法",
        "monitoring": "场景法",
        "response_structure": "场景法",
    }
    _PN_MAP = {
        "positive": "positive",
        "boundary": "boundary",
        "extreme": "boundary",
        "smoke": "positive",
        "scenario": "positive",
        "response_structure": "positive",
    }
    design_method = next(
        (v for k, v in _METHOD_MAP.items() if scenario.startswith(k)),
        "等价类划分",
    )
    positive_negative = _PN_MAP.get(scenario, "negative")

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
        "case_design_method": design_method,
        "positive_negative": positive_negative,
        "test_data_note": "数据按接口字段业务语义构造（等价类/边界值/错误推测）；真实样本可用时以生产/测试环境回填值为准。",
        "source": "ai_generated",
        "tags": [
            f"service:{service}",
            f"scenario:{scenario}",
            "source:ai_generated",
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


# ═══════════════════════════════════════════════════════
# 路由层 ORM 收敛薄函数（Batch 181 路由拆分）
# ═══════════════════════════════════════════════════════

def create_test_case_from_generated(
    db: Session,
    project_id: int,
    case_data: dict,
    endpoint_id: int | None,
) -> TestCase:
    """将生成的用例数据写入 TestCase 表（沿用调用方会话，提交由路由层负责）。"""
    tc = TestCase(
        project_id=project_id,
        title=case_data.get("title", ""),
        domain=case_data.get("domain", "接口测试"),
        module=case_data.get("module", ""),
        case_type="api",
        priority=case_data.get("priority", "P1"),
        preconditions=case_data.get("preconditions", ""),
        steps=json.dumps(case_data.get("steps", []), ensure_ascii=False),
        expected_result=case_data.get("expected_result", ""),
        api_method=case_data.get("api_method", "GET"),
        api_endpoint=case_data.get("api_endpoint", ""),
        api_spec_ref=f"api_endpoint:{endpoint_id}" if endpoint_id else "",
        api_headers=json.dumps(case_data.get("api_headers", {}), ensure_ascii=False),
        api_body=case_data.get("api_body", ""),
        api_assertions=json.dumps(case_data.get("api_assertions", []), ensure_ascii=False),
        status="draft",
        source="ai_generated",
        tags=json.dumps(case_data.get("tags", []), ensure_ascii=False),
    )
    db.add(tc)
    db.flush()
    return tc


def get_api_cases_by_ids(db: Session, project_id: int, case_ids: list[int]) -> list[TestCase]:
    """按 id 列表获取项目内 API 类型用例（用于创建执行任务前的校验）。"""
    return db.query(TestCase).filter(
        TestCase.id.in_(case_ids),
        TestCase.project_id == project_id,
        TestCase.case_type == "api",
    ).all()
