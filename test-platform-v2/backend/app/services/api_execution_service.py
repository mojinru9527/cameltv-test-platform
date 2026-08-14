"""API 测试执行引擎 — 服务端 HTTP 请求 + 变量替换 + 断言。"""
from __future__ import annotations

import copy
import ipaddress
import json
import re
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from sqlalchemy.orm import Session

from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
from app.models.test_case import TestCase
from app.services.environment_service import resolve_variables

# Column variable pattern for dataset parameterized execution
_COL_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")

# ── 配置 ──
DEFAULT_TIMEOUT = 30  # seconds
MAX_RESPONSE_BODY_SIZE = 500 * 1024  # 500 KB (max stored in raw_body)
BODY_PREVIEW_MAX_SIZE = 4096  # chars for response_snapshot.body_preview
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token", "token"}
SENSITIVE_MASK = "***"
UNSUPPORTED_BODY_MASK = "[REDACTED_UNSUPPORTED_BODY]"
SENSITIVE_FIELD_NAMES = {
    "authorization", "cookie", "set_cookie", "x_api_key", "x_auth_token",
    "token", "access_token", "refresh_token", "api_key", "apikey",
    "password", "passwd", "secret", "client_secret", "private_key",
}

# ═══════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════

def execute_api_case(
    db: Session,
    case_id: int,
    *,
    project_id: int = 0,
    environment_id: int | None = None,
    dataset_id: int | None = None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
    _dep_chain: frozenset[int] | None = None,
) -> dict:
    """执行已保存的 API 用例，返回执行结果。若提供 dataset_id 则进行参数化批量执行。"""
    case = db.get(TestCase, case_id)
    if not case or (project_id and case.project_id != project_id):
        raise ValueError(f"用例 #{case_id} 不存在")

    if case.case_type != "api":
        raise ValueError(f"用例 #{case_id} 不是 API 类型 (当前: {case.case_type})")

    # C147-8: 未显式指定数据集时使用用例默认绑定
    if dataset_id is None:
        dataset_id = getattr(case, "dataset_id", None)

    # 解析数据
    headers = _safe_json(case.api_headers, {})
    body = case.api_body or ""
    assertions = _safe_json(case.api_assertions, [])

    # 构造 request
    
    # C107-2：前置接口依赖解析（$prev.{id}.{path} 变量注入）
    dep_ids = _safe_json(getattr(case, "depends_on_ids", "") or "[]", [])
    if dep_ids:
        dep_responses = _resolve_dependencies(
            db, dep_ids,
            project_id=project_id,
            environment_id=environment_id,
            confirm_prod=confirm_prod,
            has_execute_prod=has_execute_prod,
            _dep_chain=(_dep_chain or frozenset()) | {case_id},
        )
    else:
        dep_responses = {}

    request_def = {
        "method": case.api_method or "GET",
        "url": case.api_endpoint or "",
        "headers": headers,
        "body": body,
    }

    if dep_responses:
        request_def = _apply_dependency_variables(request_def, dep_responses)
    if dataset_id:
        return _execute_with_dataset(db, request_def, assertions, environment_id, dataset_id,
                                     project_id=project_id,
                                     confirm_prod=confirm_prod, has_execute_prod=has_execute_prod,
                                     require_release_assertions=case.review_status == "approved")
    return _do_execute(db, request_def, assertions, environment_id=environment_id,
                       project_id=project_id,
                       confirm_prod=confirm_prod, has_execute_prod=has_execute_prod,
                       require_release_assertions=case.review_status == "approved")

def quick_execute(
    db: Session,
    request_def: dict,
    *,
    assertions: list[dict] | None = None,
    project_id: int = 0,
    environment_id: int | None = None,
    dataset_id: int | None = None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
    require_release_assertions: bool = False,
) -> dict:
    """即时执行（不依赖已保存用例），用于调试面板。若提供 dataset_id 则批量执行。"""
    if dataset_id:
        return _execute_with_dataset(db, request_def, assertions or [], environment_id, dataset_id,
                                     project_id=project_id,
                                     confirm_prod=confirm_prod, has_execute_prod=has_execute_prod,
                                     require_release_assertions=require_release_assertions)
    return _do_execute(db, request_def, assertions or [], environment_id=environment_id,
                       project_id=project_id,
                       confirm_prod=confirm_prod, has_execute_prod=has_execute_prod,
                       require_release_assertions=require_release_assertions)

# ═══════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════

def _do_execute(
    db: Session,
    request_def: dict,
    assertions: list[dict],
    *,
    environment_id: int | None = None,
    project_id: int = 0,
    dataset_row_index: int | None = None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
    require_release_assertions: bool = False,
) -> dict:
    """核心执行流程：解析变量 → 生产保护检查 → 发请求 → 跑断言 → 汇总结果。"""
    execution_id = f"APIEXEC-{uuid.uuid4().hex[:12].upper()}"
    method = (request_def.get("method") or "GET").upper()
    url = request_def.get("url") or ""
    headers = request_def.get("headers") or {}
    body = request_def.get("body") or ""
    query_params = request_def.get("query_params") or {}

    assertion_contract_error = _assertion_contract_error(
        assertions,
        require_release_assertions=require_release_assertions,
    )
    if assertion_contract_error:
        return _error_result(
            assertion_contract_error,
            error_type="INVALID_CASE",
            environment_id=environment_id,
            execution_id=execution_id,
        )

    # 0. 环境必须属于当前项目；内部调用也不得退回裸 environment_id。
    if environment_id:
        from app.services.environment_service import get_environment

        if not project_id or not get_environment(db, environment_id, project_id):
            return _error_result(
                "环境不存在或不属于当前项目",
                error_type="TARGET_POLICY",
                environment_id=environment_id,
                execution_id=execution_id,
            )

    # 0.1 生产环境保护检查
    allowed, prod_msg = _check_prod_protection(db, method, environment_id, confirm_prod, has_execute_prod)
    if not allowed:
        return _error_result(
            prod_msg,
            error_type="POLICY_DENIED",
            environment_id=environment_id,
            execution_id=execution_id,
        )

    # 1. 变量替换
    if environment_id:
        url = resolve_variables(db, environment_id, project_id, url)
        body = resolve_variables(db, environment_id, project_id, body)
        query_params = _resolve_mapping_variables(
            db, environment_id, project_id, query_params,
        )
        resolved_headers = {}
        for k, v in headers.items():
            k2 = resolve_variables(db, environment_id, project_id, k)
            v2 = resolve_variables(db, environment_id, project_id, str(v))
            if k2 is None or v2 is None:
                return _error_result(
                    "环境不存在或不属于当前项目",
                    error_type="TARGET_POLICY",
                    environment_id=environment_id,
                    execution_id=execution_id,
                )
            resolved_headers[k2] = v2
        headers = resolved_headers

    # 2. 解析最终 URL
    resolved_url = _resolve_url(db, environment_id, url)
    resolved_url = _append_query_params(resolved_url, query_params)

    # 2.5 SSRF 防护检查
    try:
        _validate_target_url(db, environment_id, project_id, resolved_url)
    except ValueError as exc:
        return _error_result(
            str(exc),
            error_type="TARGET_POLICY",
            environment_id=environment_id,
            resolved_url=resolved_url,
            execution_id=execution_id,
        )

    # 3. 构建请求快照（执行前）
    request_snapshot = _build_request_snapshot(
        method=method,
        original_url=request_def.get("url", ""),
        resolved_url=resolved_url,
        headers=headers,
        body=body,
        query_params=query_params,
        environment_id=environment_id,
        dataset_row_index=dataset_row_index,
        execution_id=execution_id,
    )

    # 4. 发起 HTTP 请求
    start = time.perf_counter()
    try:
        resp = _request_with_target_policy(
            db,
            method=method,
            url=resolved_url,
            headers=_prepare_headers(headers, body),
            body=body,
            environment_id=environment_id,
            project_id=project_id,
        )
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # 读取响应体（限大小）
        raw_body = _safe_read_body(resp)
        try:
            response_data = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError:
            response_data = raw_body

        # 提取响应头
        resp_headers = {k: v for k, v in resp.headers.items()}

    except ValueError as exc:
        return _error_result(
            str(exc), request_snapshot,
            error_type="TARGET_POLICY",
            environment_id=environment_id,
            resolved_url=resolved_url,
            execution_id=execution_id,
        )
    except httpx.TimeoutException:
        return _error_result(
            "请求超时 (30s)", request_snapshot,
            error_type="TIMEOUT",
            environment_id=environment_id,
            resolved_url=resolved_url,
            execution_id=execution_id,
        )
    except httpx.ConnectError as e:
        return _error_result(
            f"连接失败: {e}", request_snapshot,
            error_type="NETWORK_ERROR",
            environment_id=environment_id,
            resolved_url=resolved_url,
            execution_id=execution_id,
        )
    except Exception as e:
        return _error_result(
            f"请求异常: {type(e).__name__}: {e}", request_snapshot,
            error_type="NETWORK_ERROR",
            environment_id=environment_id,
            resolved_url=resolved_url,
            execution_id=execution_id,
        )

    # 5. 执行断言
    assertion_results = _run_assertions(
        assertions,
        status_code=resp.status_code,
        response_data=response_data,
        raw_body=raw_body,
        duration_ms=duration_ms,
        response_headers=resp_headers,
    )
    all_pass = all(a["passed"] for a in assertion_results)
    assertion_summary = _assertion_summary(assertion_results)

    # 6. 构建响应快照
    full_body = raw_body if raw_body else ""
    body_size = len(raw_body) if raw_body else 0
    body_truncated = body_size > MAX_RESPONSE_BODY_SIZE
    safe_response_headers = _redact_evidence(resp_headers)
    body_preview = _snapshot_body(full_body)
    response_snapshot = {
        "status_code": resp.status_code,
        "headers": safe_response_headers,
        "body_preview": _truncate_for_preview(body_preview, BODY_PREVIEW_MAX_SIZE),
        "body_size_bytes": body_size,
        "truncated": body_truncated or (len(full_body) > BODY_PREVIEW_MAX_SIZE),
        "content_type": resp_headers.get("content-type", ""),
    }

    return {
        "status": "ok",
        "status_code": resp.status_code,
        "response_headers": resp_headers,
        "response_body": response_data,
        "raw_body": raw_body if not isinstance(response_data, dict) else None,
        "duration_ms": duration_ms,
        "assertions": assertion_results,
        "all_pass": all_pass,
        "assertion_summary": assertion_summary,
        "environment_id": environment_id,
        "resolved_url": _redact_url_query(resolved_url),
        "error_type": "" if all_pass else "ASSERTION_FAILED",
        "execution_id": execution_id,
        "request_snapshot": request_snapshot,
        "response_snapshot": response_snapshot,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

# ── 断言引擎 ──────────────────────────────────────────

def _run_assertions(
    assertions: list[dict],
    *,
    status_code: int,
    response_data: Any,
    raw_body: str,
    duration_ms: float,
    response_headers: dict | None = None,
) -> list[dict]:
    """执行所有断言规则，返回结果列表。支持 status_code/jsonpath/regex/response_time/header/json_schema/type/array_length。"""
    results = []
    for rule in assertions:
        atype = rule.get("type", "")
        if atype == "status_code":
            r = _assert_status_code(rule, status_code)
        elif atype == "response_time":
            r = _assert_response_time(rule, duration_ms)
        elif atype == "jsonpath":
            r = _assert_jsonpath(rule, response_data)
        elif atype == "regex":
            r = _assert_regex(rule, raw_body)
        elif atype == "header":
            r = _assert_header(rule, response_headers or {})
        elif atype == "json_schema":
            r = _assert_json_schema(rule, response_data)
        elif atype == "type":
            r = _assert_type(rule, response_data)
        elif atype == "array_length":
            r = _assert_array_length(rule, response_data)
        elif atype == "response_structure":
            r = _assert_response_structure(rule, response_data)
        else:
            r = {"type": atype, "expected": rule.get("expected"), "actual": None,
                 "passed": False, "message": f"未知断言类型: {atype}"}
        results.append(r)
    return results

def _assertion_contract_error(
    assertions: list[dict],
    *,
    require_release_assertions: bool,
) -> str:
    if not assertions:
        return "API 用例至少需要一个有效断言"
    if not require_release_assertions:
        return ""

    has_status = any(rule.get("type") == "status_code" for rule in assertions)
    jsonpath_rules = [rule for rule in assertions if rule.get("type") == "jsonpath"]
    business_paths = {
        str(rule.get("path") or "").casefold()
        for rule in jsonpath_rules
        if str(rule.get("path") or "").casefold().endswith((".code", ".business_code"))
    }
    has_business_code = bool(business_paths)
    has_core_field = any(
        str(rule.get("path") or "").casefold() not in business_paths
        and str(rule.get("path") or "") not in {"", "$"}
        for rule in jsonpath_rules
    )

    missing = []
    if not has_status:
        missing.append("status")
    if not has_business_code:
        missing.append("business-code")
    if not has_core_field:
        missing.append("core-field")
    if missing:
        return f"approved release API case missing assertions: {', '.join(missing)}"
    return ""

def _assert_status_code(rule: dict, status_code: int) -> dict:
    expected = rule.get("expected", 200)
    op = rule.get("operator", "eq")
    passed = _compare(status_code, expected, op)
    return {
        "type": "status_code",
        "expected": expected,
        "operator": op,
        "actual": status_code,
        "passed": passed,
        "message": f"HTTP {status_code} {_op_label(op)} {expected}" + (" ✓" if passed else " ✗"),
    }

def _assert_response_time(rule: dict, duration_ms: float) -> dict:
    expected = rule.get("expected", 3000)
    op = rule.get("operator", "lt")
    passed = _compare(duration_ms, expected, op)
    return {
        "type": "response_time",
        "expected": expected,
        "operator": op,
        "actual": f"{duration_ms}ms",
        "passed": passed,
        "message": f"{duration_ms}ms {_op_label(op)} {expected}ms" + (" ✓" if passed else " ✗"),
    }

def _assert_jsonpath(rule: dict, data: Any) -> dict:
    path = rule.get("path", "$")
    expected = rule.get("expected")
    op = rule.get("operator", "eq")

    actual = _jsonpath_get(data, path)
    exists = actual is not _JSONPATH_MISSING

    if op == "exists":
        passed = exists
        return {
            "type": "jsonpath", "path": path,
            "expected": "exists",
            "actual": "<present>" if exists else "<missing>",
            "passed": passed,
            "message": f"{path} {'存在' if exists else '不存在'}" + (" ✓" if passed else " ✗"),
        }

    if not exists:
        return {
            "type": "jsonpath", "path": path,
            "expected": expected, "actual": "<missing>",
            "passed": False,
            "message": f"{path} 不存在 ✗",
        }

    passed = _compare(actual, expected, op)
    return {
        "type": "jsonpath", "path": path,
        "expected": expected,
        "operator": op,
        "actual": actual,
        "passed": passed,
        "message": f"{path}: {actual} {_op_label(op)} {expected}" + (" ✓" if passed else " ✗"),
    }

def _assert_regex(rule: dict, text: str) -> dict:
    pattern = rule.get("pattern") or rule.get("expected", "")
    try:
        m = re.search(pattern, text or "")
    except re.error as e:
        return {
            "type": "regex", "pattern": pattern,
            "expected": f"regex: {pattern}",
            "actual": f"<regex error: {e}>",
            "passed": False,
            "message": f"正则语法错误: {e}",
        }
    passed = m is not None
    return {
        "type": "regex", "pattern": pattern,
        "expected": f"match /{pattern}/",
        "actual": f"<{'matched' if m else 'no match'}>",
        "passed": passed,
        "message": f"regex /{pattern}/ {'匹配' if passed else '不匹配'}" + (" ✓" if passed else " ✗"),
    }

# ── 新增断言类型 (Task 4) ──────────────────────────────

def _assert_header(rule: dict, response_headers: dict) -> dict:
    """断言响应头。"""
    key = rule.get("key", "")
    expected = rule.get("expected", "")
    op = rule.get("operator", "contains")
    actual = response_headers.get(key)
    if actual is None:
        # 尝试大小写不敏感查找
        for hk, hv in response_headers.items():
            if hk.lower() == key.lower():
                actual = hv
                break
    exists = actual is not None

    if op == "exists":
        return {
            "type": "header", "key": key,
            "expected": "exists",
            "actual": f"<{'present' if exists else 'missing'}>",
            "passed": exists,
            "message": f"Header {key} {'存在' if exists else '不存在'}" + (" ✓" if exists else " ✗"),
        }

    if not exists:
        return {
            "type": "header", "key": key,
            "expected": expected, "actual": "<missing>",
            "passed": False,
            "message": f"Header {key} 不存在 ✗",
        }

    passed = _compare(str(actual), expected, op)
    return {
        "type": "header", "key": key,
        "expected": f"{op} {expected}",
        "actual": actual,
        "passed": passed,
        "message": f"Header {key}: {actual} {_op_label(op)} {expected}" + (" ✓" if passed else " ✗"),
    }

def _assert_json_schema(rule: dict, data: Any) -> dict:
    """断言响应体符合 JSON Schema。"""
    schema = rule.get("expected")
    if not schema or not isinstance(data, dict):
        return {
            "type": "json_schema", "expected": str(schema)[:80],
            "actual": "<non-object>",
            "passed": False,
            "message": "json_schema 断言需要 object 类型的响应体 ✗",
        }

    errors = _validate_json_schema(data, schema)
    passed = len(errors) == 0
    return {
        "type": "json_schema",
        "expected": f"schema with {len(schema.get('properties', {}))} fields",
        "actual": f"<{'valid' if passed else ', '.join(errors[:3])}>",
        "passed": passed,
        "message": f"JSON Schema {'✓' if passed else '✗: ' + '; '.join(errors[:3])}",
    }

def _validate_json_schema(data: dict, schema: dict, path: str = "$") -> list[str]:
    """轻量 JSON Schema 验证器。"""
    errors = []
    stype = schema.get("type", "")
    if stype and stype != "object":
        return errors  # 仅验证顶层 object

    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"{path}.{field} 缺失")

    properties = schema.get("properties", {})
    for field, prop in properties.items():
        if field not in data:
            continue
        val = data[field]
        expected_type = prop.get("type", "")
        if expected_type == "integer" and not isinstance(val, int):
            errors.append(f"{path}.{field} 类型应为 integer，实际 {type(val).__name__}")
        elif expected_type == "number" and not isinstance(val, (int, float)):
            errors.append(f"{path}.{field} 类型应为 number，实际 {type(val).__name__}")
        elif expected_type == "string" and not isinstance(val, str):
            errors.append(f"{path}.{field} 类型应为 string，实际 {type(val).__name__}")
        elif expected_type == "boolean" and not isinstance(val, bool):
            errors.append(f"{path}.{field} 类型应为 boolean，实际 {type(val).__name__}")
        elif expected_type == "array" and not isinstance(val, list):
            errors.append(f"{path}.{field} 类型应为 array，实际 {type(val).__name__}")
        elif expected_type == "object" and not isinstance(val, dict):
            errors.append(f"{path}.{field} 类型应为 object，实际 {type(val).__name__}")

    return errors

def _assert_type(rule: dict, data: Any) -> dict:
    """断言 JSONPath 字段类型。"""
    path = rule.get("path", "$")
    expected_type = rule.get("expected", "string")
    actual = _jsonpath_get(data, path)
    if actual is _JSONPATH_MISSING:
        return {
            "type": "type", "path": path,
            "expected": expected_type, "actual": "<missing>",
            "passed": False,
            "message": f"{path} 不存在 ✗",
        }

    type_map = {
        "string": str, "str": str,
        "number": (int, float), "integer": int, "int": int,
        "boolean": bool, "bool": bool,
        "array": list, "list": list,
        "object": dict, "dict": dict,
        "null": type(None),
    }
    expected_cls = type_map.get(expected_type, str)
    passed = isinstance(actual, expected_cls)
    return {
        "type": "type", "path": path,
        "expected": f"type {expected_type}",
        "actual": type(actual).__name__,
        "passed": passed,
        "message": f"{path} 类型: {type(actual).__name__} {'==' if passed else '!='} {expected_type}" + (" ✓" if passed else " ✗"),
    }

_DEP_VAR_RE = re.compile(r"\$prev\.(\d+)\.([A-Za-z0-9_.\[\]\-]+)")

def _resolve_dependencies(
    db: Session,
    dep_ids: list,
    *,
    project_id: int,
    environment_id: int | None,
    confirm_prod: bool,
    has_execute_prod: bool,
    _dep_chain: frozenset[int],
) -> dict:
    """C107-2：执行前置接口用例，返回 {dep_case_id: response_json}（递归支持多级，环检测）。"""
    results: dict[str, Any] = {}
    for raw in dep_ids:
        try:
            dep_id = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"非法依赖用例 id: {raw}") from None
        if dep_id in _dep_chain:
            raise ValueError(f"接口依赖存在环: {dep_id}")
        dep = db.get(TestCase, dep_id)
        if not dep:
            raise ValueError(f"依赖用例 #{dep_id} 不存在")
        r = execute_api_case(
            db, dep_id,
            project_id=project_id,
            environment_id=environment_id,
            confirm_prod=confirm_prod,
            has_execute_prod=has_execute_prod,
            _dep_chain=_dep_chain | {dep_id},
        )
        if not r.get("all_pass"):
            raise ValueError(f"依赖用例 #{dep_id} 执行失败: {r.get('error') or r.get('status_code')}")
        results[str(dep_id)] = r.get("response_body")
    return results

def _apply_dependency_variables(request_def: dict, dep_responses: dict) -> dict:
    """把请求中的 $prev.{dep_id}.{jsonpath} 替换为前置响应值。"""
    def _replace(m) -> str:
        dep_id, path = m.group(1), m.group(2)
        node = dep_responses.get(dep_id)
        if node is None:
            return m.group(0)
        val = _jsonpath_get(node, path)
        if val is _JSONPATH_MISSING:
            return m.group(0)
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False)
        return str(val)

    out = dict(request_def)
    out["url"] = _DEP_VAR_RE.sub(_replace, out.get("url") or "")
    out["body"] = _DEP_VAR_RE.sub(_replace, out.get("body") or "")
    return out

def _assert_response_structure(rule: dict, data: Any) -> dict:
    """响应结构断言（Batch 112）：exists / not_empty / is_object_or_array / len_lte。

    语义与 scripts/sports/execute-interface-cases.py::_assert_structure 对齐（97/97 已验证）：
    - envelope 键缺失 -> 失败；
    - 200 信封下 data.* 动态缺失 -> warning（passed=True，不判失败，B110-5 口径）；
    - records[0].* 记录字段以键存在为准（实时数据字段值可合法为空）；
    - len_lte 超界 -> 失败；hint 型为信息性提示不参与判定。
    """
    path = str(rule.get("path") or "")
    kind = str(rule.get("assert") or "exists")

    if kind == "hint" or not path:
        return {
            "type": "response_structure",
            "path": path,
            "assert": kind,
            "expected": "info",
            "actual": "-",
            "passed": True,
            "warning": "信息性提示，不参与判定",
        }

    node = _structure_resolve(data, path)
    dynamic_data_path = path == "data" or path.startswith("data.")
    record_field = "records[" in path or "[0]" in path

    if kind in ("exists", "not_empty", "is_object_or_array"):
        if node is _JSONPATH_MISSING:
            if dynamic_data_path:
                return _structure_result(
                    rule, node, True, f"{path} {kind} 缺失（动态数据，200 信封保留）",
                )
            return _structure_result(rule, node, False, f"{path} {kind} 失败")
        if kind == "exists":
            return _structure_result(rule, node, True, "")
        if kind == "is_object_or_array":
            ok = isinstance(node, (dict, list))
            return _structure_result(
                rule, node, ok, "" if ok else f"{path} 非对象/数组",
            )
        if kind == "not_empty":
            if record_field:
                return _structure_result(rule, node, True, "记录字段以键存在为准")
            if node in ("", [], {}, None):
                return _structure_result(rule, node, False, f"{path} 为空")
            return _structure_result(rule, node, True, "")

    if kind == "len_lte":
        expected = int(rule.get("expected") or 0)
        if isinstance(node, list) and len(node) > expected:
            return _structure_result(
                rule, node, False, f"{path} 长度 {len(node)} > {expected}",
            )
        return _structure_result(rule, node, True, "")

    return _structure_result(rule, node, False, f"未知断言类型: {kind}")

def _structure_resolve(data: Any, path: str) -> Any:
    """按点号路径解析响应结构节点，缺失返回 _JSONPATH_MISSING。

    兼容 data.records[0].field、data[0]、data.records[]（空下标跳过）。
    """
    node = data
    for seg in _structure_split(path):
        if node is _JSONPATH_MISSING:
            return _JSONPATH_MISSING
        if isinstance(node, dict):
            if isinstance(seg, int):
                return _JSONPATH_MISSING
            node = node.get(seg, _JSONPATH_MISSING)
        elif isinstance(node, list):
            if isinstance(seg, int):
                node = node[seg] if 0 <= seg < len(node) else _JSONPATH_MISSING
            else:
                return _JSONPATH_MISSING
        else:
            return _JSONPATH_MISSING
    return node

def _structure_split(path: str) -> list:
    """把 data.records[0].id 拆成 ['data','records',0,'id']，空 [] 段跳过。"""
    parts: list = []
    for seg in path.split("."):
        seg = seg.strip()
        if not seg or seg == "[]":
            continue
        if "[" in seg and seg.endswith("]"):
            name, _, idx = seg.partition("[")
            idx = idx.rstrip("]")
            if name:
                parts.append(name)
            if idx.isdigit():
                parts.append(int(idx))
        else:
            parts.append(seg)
    return parts

def _structure_result(rule: dict, actual: Any, passed: bool, message: str) -> dict:
    out = {
        "type": "response_structure",
        "path": rule.get("path", ""),
        "assert": rule.get("assert", "exists"),
        "expected": rule.get("expected"),
        "actual": "<present>" if actual is not _JSONPATH_MISSING else "<missing>",
        "passed": passed,
    }
    if message:
        out["message"] = message
        if passed:
            out["warning"] = message
    return out

def _assert_array_length(rule: dict, data: Any) -> dict:
    """断言 JSONPath 数组长度。"""
    path = rule.get("path", "$")
    expected = rule.get("expected", 0)
    op = rule.get("operator", "gte")
    actual = _jsonpath_get(data, path)
    if actual is _JSONPATH_MISSING:
        return {
            "type": "array_length", "path": path,
            "expected": f"{op} {expected}", "actual": "<missing>",
            "passed": False,
            "message": f"{path} 不存在 ✗",
        }
    if not isinstance(actual, list):
        return {
            "type": "array_length", "path": path,
            "expected": f"{op} {expected}", "actual": f"<non-array: {type(actual).__name__}>",
            "passed": False,
            "message": f"{path} 不是数组 ✗",
        }

    length = len(actual)
    passed = _compare(length, expected, op)
    return {
        "type": "array_length", "path": path,
        "expected": f"{op} {expected}",
        "actual": length,
        "passed": passed,
        "message": f"{path} 长度 {length} {_op_label(op)} {expected}" + (" ✓" if passed else " ✗"),
    }

# ── 比较 ──────────────────────────────────────────────

def _compare(actual: Any, expected: Any, op: str) -> bool:
    """通用比较器。"""
    equal = actual == expected
    numeric_types = (int, float)
    one_numeric_one_string = (
        isinstance(actual, numeric_types)
        and not isinstance(actual, bool)
        and isinstance(expected, str)
    ) or (
        isinstance(expected, numeric_types)
        and not isinstance(expected, bool)
        and isinstance(actual, str)
    )
    if one_numeric_one_string:
        try:
            equal = float(actual) == float(expected)
        except (TypeError, ValueError):
            equal = False
    if op == "eq" or op == "equals":
        return equal
    if op == "neq" or op == "not_equals":
        return not equal
    if op == "gt":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if op == "lt":
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    if op == "gte":
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    if op == "lte":
        try:
            return float(actual) <= float(expected)
        except (TypeError, ValueError):
            return False
    if op == "contains":
        return str(expected) in str(actual)
    return False

def _op_label(op: str) -> str:
    return {"eq": "=", "equals": "=", "neq": "≠", "gt": ">", "lt": "<",
            "gte": "≥", "lte": "≤", "contains": "含"}.get(op, op)

# ── 轻量 JSONPath ─────────────────────────────────────

_JSONPATH_MISSING = object()

def _jsonpath_get(data: Any, path: str) -> Any:
    """简易 JSONPath 解析，支持 $.key.sub、$.arr[0]、$.arr[*].key。"""
    if not path or path == "$":
        return data

    # Strip leading "$."
    expr = path[2:] if path.startswith("$.") else path

    current = data
    for segment in _split_path(expr):
        if current is _JSONPATH_MISSING:
            return _JSONPATH_MISSING
        current = _resolve_segment(current, segment)
    return current

def _split_path(expr: str) -> list[str]:
    """将 'key.sub[0].val' 分割为 ['key','sub','[0]','val']。"""
    parts = []
    i = 0
    buf = ""
    while i < len(expr):
        ch = expr[i]
        if ch == ".":
            if buf:
                parts.append(buf)
                buf = ""
        elif ch == "[":
            if buf:
                parts.append(buf)
                buf = ""
            j = expr.index("]", i)
            parts.append(expr[i:j + 1])
            i = j
        else:
            buf += ch
        i += 1
    if buf:
        parts.append(buf)
    return parts

def _resolve_segment(current: Any, seg: str) -> Any:
    """基于当前值解析一个路径段。"""
    # Array index: [0], [*], [-1]
    if seg.startswith("[") and seg.endswith("]"):
        inner = seg[1:-1]
        if not isinstance(current, list):
            return _JSONPATH_MISSING
        if inner == "*":
            # Wildcard: return first match or list of values
            return current  # caller can iterate, but for assertions return all
        try:
            idx = int(inner)
            if 0 <= idx < len(current):
                return current[idx]
            if idx < 0 and abs(idx) <= len(current):
                return current[idx]
            return _JSONPATH_MISSING
        except (ValueError, IndexError):
            return _JSONPATH_MISSING

    # Dict key
    if isinstance(current, dict):
        return current.get(seg, _JSONPATH_MISSING)

    return _JSONPATH_MISSING

# ── 辅助 ──────────────────────────────────────────────

def _safe_json(raw: str, default: Any = None) -> Any:
    """安全解析 JSON 字符串。"""
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default

def _safe_read_body(resp: httpx.Response) -> str:
    """安全读取响应体，限制大小。"""
    try:
        raw = resp.text
        if len(raw) > MAX_RESPONSE_BODY_SIZE:
            return raw[:MAX_RESPONSE_BODY_SIZE] + f"\n... (截断, total {len(raw)} bytes)"
        return raw
    except Exception:
        return "[无法读取响应体]"

def _prepare_headers(headers: dict, body: str) -> dict:
    """准备请求头，自动设置 Content-Type"""
    h = dict(headers) if headers else {}
    if body and "content-type" not in {k.lower() for k in h}:
        h["Content-Type"] = "application/json"
    return h

def _resolve_mapping_variables(
    db: Session,
    environment_id: int,
    project_id: int,
    value: Any,
) -> Any:
    """Resolve environment variables recursively without coercing numeric values."""
    if isinstance(value, dict):
        return {
            str(_resolve_mapping_variables(db, environment_id, project_id, key)):
            _resolve_mapping_variables(db, environment_id, project_id, item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _resolve_mapping_variables(db, environment_id, project_id, item)
            for item in value
        ]
    if isinstance(value, str):
        return resolve_variables(db, environment_id, project_id, value)
    return value

def _append_query_params(url: str, query_params: dict[str, Any]) -> str:
    if not query_params:
        return url
    parsed = urlparse(url)
    existing = parse_qsl(parsed.query, keep_blank_values=True)
    additions: list[tuple[str, Any]] = []
    for key, value in query_params.items():
        if isinstance(value, list):
            additions.extend((key, item) for item in value)
        else:
            additions.append((key, value))
    query = urlencode([*existing, *additions], doseq=True)
    return urlunparse(parsed._replace(query=query))

def _resolve_url(db: Session, environment_id: int | None, url: str) -> str:
    """将相对路径与环境 base_url 拼接为完整 URL。
    - 完整 URL (http/https 开头) 直接返回
    - 相对路径与环境 base_url 拼接
    - 无环境时给相对路径添加 http:// 前缀
    """
    if url.startswith(("http://", "https://")):
        return url

    if environment_id:
        from app.models.environment import Environment
        env = db.get(Environment, environment_id)
        if env and env.base_url:
            return env.base_url.rstrip("/") + "/" + url.lstrip("/")

    return url if url.startswith("http") else f"http://{url}"

# ── SSRF 防护 ────────────────────────────────────────────

# 禁止访问的 IP 范围（RFC 1918 + 回环 + 链路本地 + 特殊用途）
_SSRF_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # 回环
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 A 类
    ipaddress.ip_network("172.16.0.0/12"),    # RFC 1918 B 类
    ipaddress.ip_network("192.168.0.0/16"),   # RFC 1918 C 类
    ipaddress.ip_network("169.254.0.0/16"),   # 链路本地
    ipaddress.ip_network("0.0.0.0/8"),        # 当前网络
    ipaddress.ip_network("::1/128"),          # IPv6 回环
    ipaddress.ip_network("fc00::/7"),         # IPv6 唯一本地
    ipaddress.ip_network("fe80::/10"),        # IPv6 链路本地
]

def _is_private_ip(host: str) -> bool:
    """检查 host 是否指向私有/内部 IP（SSRF 防护）。"""
    try:
        # 尝试直接解析为 IP
        addr = ipaddress.ip_address(host)
    except ValueError:
        # DNS 解析 → 获取第一个 IP
        try:
            addr = ipaddress.ip_address(socket.gethostbyname(host))
        except (socket.gaierror, OSError):
            return False  # 无法解析，放行（后续 httpx 会报错）

    return any(addr in net for net in _SSRF_BLOCKED_NETWORKS)

def _validate_url_no_ssrf(url: str, allow_env_urls: bool = True) -> None:
    """验证 URL 不指向内部/私有 IP，防止 SSRF 攻击。

    Raises:
        ValueError: URL 指向被禁止的内部 IP
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError(f"无法解析 URL: {url}")

    host = parsed.hostname
    if not host:
        raise ValueError(f"URL 缺少主机名: {url}")

    if _is_private_ip(host):
        raise ValueError(
            f"SSRF 防护：禁止访问内部地址 {host}。"
            f"如需访问内部服务，请配置测试环境 base_url。"
        )

def _effective_port(parsed) -> int | None:
    if parsed.port is not None:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    if parsed.scheme == "http":
        return 80
    return None

def _validate_target_url(
    db: Session,
    environment_id: int | None,
    project_id: int,
    url: str,
) -> None:
    """Validate every outbound target, including redirects, before network I/O."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"无法解析 URL: {url}")

    if environment_id is None:
        _validate_url_no_ssrf(url)
        return

    from app.services.environment_service import get_environment

    environment = get_environment(db, environment_id, project_id) if project_id else None
    if not environment:
        raise ValueError("环境不存在或不属于当前项目")

    allowed = urlparse(environment.get("base_url") or "")
    same_target = (
        allowed.scheme in {"http", "https"}
        and allowed.hostname is not None
        and parsed.scheme == allowed.scheme
        and parsed.hostname.casefold() == allowed.hostname.casefold()
        and _effective_port(parsed) == _effective_port(allowed)
    )
    if not same_target:
        raise ValueError(
            "target URL must match the project environment host allowlist"
        )

def _request_with_target_policy(
    db: Session,
    *,
    method: str,
    url: str,
    headers: dict,
    body: str,
    environment_id: int | None,
    project_id: int,
) -> httpx.Response:
    """Send at most ten hops and revalidate each redirect target."""
    current_method = method
    current_url = url
    current_body = body
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=False) as client:
        for _hop in range(10):
            response = client.request(
                method=current_method,
                url=current_url,
                headers=headers,
                content=(
                    current_body
                    if current_method in ("POST", "PUT", "PATCH")
                    else None
                ),
            )
            if not response.is_redirect:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            next_url = urljoin(current_url, location)
            _validate_target_url(db, environment_id, project_id, next_url)
            if response.status_code == 303 or (
                response.status_code in {301, 302} and current_method == "POST"
            ):
                current_method = "GET"
                current_body = ""
            current_url = next_url
    raise ValueError("redirect limit exceeded")

def _assertion_summary(assertions: list[dict]) -> dict[str, int]:
    passed = sum(1 for assertion in assertions if assertion.get("passed") is True)
    return {
        "total": len(assertions),
        "passed": passed,
        "failed": len(assertions) - passed,
    }

def _error_result(
    message: str,
    request_snapshot: dict | None = None,
    *,
    error_type: str = "EXECUTION_ERROR",
    environment_id: int | None = None,
    resolved_url: str = "",
    execution_id: str | None = None,
) -> dict:
    return {
        "status": "error",
        "status_code": 0,
        "response_headers": {},
        "response_body": None,
        "raw_body": None,
        "duration_ms": 0,
        "assertions": [],
        "all_pass": False,
        "assertion_summary": {"total": 0, "passed": 0, "failed": 0},
        "error": message,
        "error_type": error_type,
        "environment_id": environment_id,
        "resolved_url": _redact_url_query(resolved_url),
        "execution_id": execution_id or f"APIEXEC-{uuid.uuid4().hex[:12].upper()}",
        "request_snapshot": request_snapshot or {},
        "response_snapshot": {},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

def _build_request_snapshot(
    *,
    method: str,
    original_url: str,
    resolved_url: str,
    headers: dict,
    body: str,
    query_params: dict[str, Any] | None = None,
    environment_id: int | None = None,
    dataset_row_index: int | None = None,
    execution_id: str | None = None,
) -> dict:
    """构建脱敏请求快照；非结构化正文默认不持久化。"""
    safe_headers = _redact_evidence(headers)
    safe_query_params = _redact_evidence(query_params or {})
    safe_body = _snapshot_body(body)
    if len(safe_body) > 10000:
        safe_body = safe_body[:10000] + f"\n... (truncated, total {len(safe_body)} bytes)"

    safe_original_url = _redact_url_query(original_url)
    safe_resolved_url = _redact_url_query(resolved_url)

    snapshot = {
        "method": method,
        "original_url": safe_original_url,
        "resolved_url": safe_resolved_url,
        "headers": safe_headers,
        "query_params": safe_query_params,
        "body": safe_body,
        "environment_id": environment_id,
        "dataset_row_index": dataset_row_index,
        "execution_id": execution_id,
        "curl": build_curl_command({
            "method": method,
            "resolved_url": safe_resolved_url,
            "original_url": safe_original_url,
            "headers": safe_headers,
            "body": safe_body,
        }),
    }
    return snapshot

def _is_sensitive_field(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
    return (
        normalized in SENSITIVE_FIELD_NAMES
        or normalized.endswith("_token")
        or normalized.endswith("_password")
        or normalized.endswith("_secret")
        or normalized.endswith("_api_key")
    )

def _redact_evidence(value: Any, *, field_name: str = "") -> Any:
    """Recursively mask sensitive evidence fields while preserving safe types."""
    if field_name and _is_sensitive_field(field_name):
        return SENSITIVE_MASK
    if isinstance(value, dict):
        return {
            key: _redact_evidence(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_evidence(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_evidence(item) for item in value]
    return value

def _snapshot_body(body: str | None) -> str:
    if not body:
        return ""
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return UNSUPPORTED_BODY_MASK
    return json.dumps(_redact_evidence(parsed), ensure_ascii=False, default=str)

def _redact_url_query(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    safe_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        safe_query.append((key, SENSITIVE_MASK if _is_sensitive_field(key) else value))
    return urlunparse(parsed._replace(query=urlencode(safe_query, doseq=True)))

# ── 生产环境保护 ──────────────────────────────────────────

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}

def _check_prod_protection(
    db: Session,
    method: str,
    environment_id: int | None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
) -> tuple[bool, str]:
    """检查生产环境保护。

    规则:
    - GET/HEAD/OPTIONS in prod: allowed (read-only)
    - POST/PUT/PATCH/DELETE in prod: require has_execute_prod AND confirm_prod=true
    """
    if not environment_id:
        return True, ""
    method_upper = method.upper()

    from app.models.environment import Environment
    env = db.get(Environment, environment_id)
    if not env:
        return True, ""  # 环境不存在由调用方处理
    if env.env_type != "prod" and not env.is_production:
        return True, ""

    # 记录生产环境执行的审计日志
    try:
        from app.services.audit_service import write_audit
        write_audit(
            db,
            project_id=env.project_id,
            action="apitest:execute_prod",
            target=f"env/{environment_id}",
            detail=f"Production {method_upper} execution on env #{environment_id} ({env.name})",
        )
    except Exception:
        pass  # 审计日志写入失败不应阻断执行

    # 读操作在生产环境始终允许
    if method_upper in READ_METHODS:
        return True, ""

    # 写操作在生产环境需要双重保护
    if method_upper not in WRITE_METHODS:
        return True, ""

    if not has_execute_prod:
        return False, (
            f"生产环境禁止执行 {method_upper} 写操作。"
            f"需要 apitest:execute_prod 权限。"
        )
    if not confirm_prod:
        return False, (
            f"生产环境执行 {method_upper} 写操作需要二次确认。"
            f"请设置 confirm_prod=true。"
        )
    return True, ""

# ── 参数化批量执行 ──────────────────────────────────────

def _execute_with_dataset(
    db: Session,
    request_def: dict,
    assertions: list[dict],
    environment_id: int | None,
    dataset_id: int,
    project_id: int = 0,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
    require_release_assertions: bool = False,
) -> dict:
    """遍历数据集每一行，逐行替换 ${column_name} 并执行，返回批量结果。"""
    from app.services.dataset_service import get_dataset_rows, get_dataset

    rows = get_dataset_rows(db, dataset_id, project_id=project_id)
    dataset = get_dataset(db, dataset_id, project_id=project_id)
    columns = json.loads(dataset["columns_meta"]) if dataset else []

    per_row_results = []
    for row_idx, row in enumerate(rows):
        # Deep-copy request_def to avoid mutation across iterations
        row_req = copy.deepcopy(request_def)
        row_assertions = copy.deepcopy(assertions)

        # Substitute ${column_name} in url, headers, body
        row_req["url"] = _substitute_columns(row_req.get("url", ""), row)
        row_req["body"] = _substitute_columns(row_req.get("body", ""), row)
        query_params = row_req.get("query_params", {})
        if isinstance(query_params, dict):
            row_req["query_params"] = {
                key: _substitute_query_value(value, row)
                for key, value in query_params.items()
            }
        headers = row_req.get("headers", {})
        if isinstance(headers, dict):
            for k, v in headers.items():
                headers[k] = _substitute_columns(str(v), row)

        # Execute
        result = _do_execute(db, row_req, row_assertions, environment_id=environment_id,
                            project_id=project_id, dataset_row_index=row_idx,
                            confirm_prod=confirm_prod,
                            has_execute_prod=has_execute_prod,
                            require_release_assertions=require_release_assertions)
        per_row_results.append({
            "row_index": row_idx,
            "row_data": _redact_evidence(row),
            "result": result,
        })

    total = len(per_row_results)
    passed = sum(1 for r in per_row_results if r["result"].get("all_pass", False))
    failed = total - passed

    return {
        "status": "ok",
        "batch_mode": True,
        "dataset_id": dataset_id,
        "columns": columns,
        "total_rows": total,
        "passed": passed,
        "failed": failed,
        "per_row": per_row_results,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

def _substitute_columns(template: str, row: dict) -> str:
    """Replace ${column_name} in template with values from the current data row."""
    def _replacer(m: re.Match) -> str:
        return str(row.get(m.group(1), m.group(0)))
    return _COL_VAR_PATTERN.sub(_replacer, template)

def _substitute_query_value(value: Any, row: dict) -> Any:
    if isinstance(value, str):
        return _substitute_columns(value, row)
    if isinstance(value, list):
        return [_substitute_query_value(item, row) for item in value]
    return value

# ── curl 复现命令生成 ────────────────────────────────────

def build_curl_command(request_snapshot: dict) -> str:
    """从请求快照生成等效 curl 命令，方便失败排查。"""
    method = (request_snapshot.get("method") or "GET").upper()
    url = request_snapshot.get("resolved_url") or request_snapshot.get("original_url") or ""
    headers = request_snapshot.get("headers") or {}
    body = request_snapshot.get("body") or ""

    parts = ["curl", "-X", method]

    # URL
    if url:
        parts.append(_shell_quote(url))

    # Headers (keep masked tokens)
    for k, v in headers.items():
        if v == SENSITIVE_MASK:
            parts.append(f"-H {_shell_quote(f'{k}: <your-token>')}")
        else:
            parts.append(f"-H {_shell_quote(f'{k}: {v}')}")

    # Body
    if body and method in ("POST", "PUT", "PATCH"):
        parts.append(f"-d {_shell_quote(str(body))}")

    return " \\\n  ".join(parts)

def _truncate_for_preview(text: str, max_chars: int) -> str:
    """截断文本用于预览，保留开头和结尾。"""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n... [truncated {len(text) - max_chars} chars] ...\n" + text[-half:]

def _shell_quote(s: str) -> str:
    """简单 shell 引号（Windows cmd 兼容：优先双引号）。"""
    escaped = s.replace('"', '\\"')
    return f'"{escaped}"'


# ═══════════════════════════════════════════════════════
# 路由层 ORM 收敛薄函数（Batch 181 路由拆分）
# ═══════════════════════════════════════════════════════

def get_task_by_id(db: Session, task_id: int) -> ApiExecutionTask | None:
    """按 id 获取执行任务（不带项目过滤，供路由区分 404/403）。"""
    return db.get(ApiExecutionTask, task_id)


def get_project_task(db: Session, task_id: int, project_id: int) -> ApiExecutionTask | None:
    """Return an execution task only when it belongs to the active project."""
    return db.query(ApiExecutionTask).filter(
        ApiExecutionTask.id == task_id,
        ApiExecutionTask.project_id == project_id,
    ).first()


def list_project_tasks(
    db: Session,
    project_id: int,
    *,
    service_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ApiExecutionTask], int]:
    """分页列出执行任务（按创建时间倒序，与路由原逻辑一致）。"""
    q = db.query(ApiExecutionTask).filter_by(project_id=project_id)
    if service_id:
        q = q.filter_by(service_id=service_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(ApiExecutionTask.created_at.desc())

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def list_task_items(db: Session, task_id: int) -> list[ApiExecutionTaskItem]:
    """列出任务明细。"""
    return db.query(ApiExecutionTaskItem).filter_by(task_id=task_id).all()


def list_failed_task_items(db: Session, task_id: int) -> list[ApiExecutionTaskItem]:
    """列出任务的失败明细。"""
    return db.query(ApiExecutionTaskItem).filter_by(
        task_id=task_id, status="failed",
    ).all()


def get_task_item(db: Session, item_id: int) -> ApiExecutionTaskItem | None:
    """按 id 获取任务明细。"""
    return db.get(ApiExecutionTaskItem, item_id)


def create_execution_task(
    db: Session,
    *,
    project_id: int,
    task_id: str,
    name: str,
    environment_id: int | None,
    service_id: int | None,
    status: str,
    total: int,
    creator_id: int,
    confirm_prod: bool,
    trigger_type: str = "manual",
) -> ApiExecutionTask:
    """创建执行任务并 flush（沿用调用方会话，提交由路由层负责）。"""
    task = ApiExecutionTask(
        project_id=project_id,
        task_id=task_id,
        name=name,
        environment_id=environment_id,
        service_id=service_id,
        status=status,
        total=total,
        creator_id=creator_id,
        confirm_prod=confirm_prod,
        trigger_type=trigger_type,
    )
    db.add(task)
    db.flush()
    return task


def add_task_items(db: Session, task_id: int, case_ids: list[int]) -> None:
    """为任务批量写入明细行（不提交，由路由层统一 commit）。"""
    for case_id in case_ids:
        db.add(ApiExecutionTaskItem(task_id=task_id, case_id=case_id))


def delete_task_items(db: Session, task_id: int) -> None:
    """删除任务的明细行（不提交，由路由层统一 commit）。"""
    db.query(ApiExecutionTaskItem).filter(ApiExecutionTaskItem.task_id == task_id).delete()
