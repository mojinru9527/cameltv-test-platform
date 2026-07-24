"""API 测试执行引擎 — 服务端 HTTP 请求 + 变量替换 + 断言。"""
from __future__ import annotations

import copy
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

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
) -> dict:
    """执行已保存的 API 用例，返回执行结果。若提供 dataset_id 则进行参数化批量执行。"""
    case = db.get(TestCase, case_id)
    if not case or (project_id and case.project_id != project_id):
        raise ValueError(f"用例 #{case_id} 不存在")

    if case.case_type != "api":
        raise ValueError(f"用例 #{case_id} 不是 API 类型 (当前: {case.case_type})")

    # 解析数据
    headers = _safe_json(case.api_headers, {})
    body = case.api_body or ""
    assertions = _safe_json(case.api_assertions, [])

    # 构造 request
    request_def = {
        "method": case.api_method or "GET",
        "url": case.api_endpoint or "",
        "headers": headers,
        "body": body,
    }

    if dataset_id:
        return _execute_with_dataset(db, request_def, assertions, environment_id, dataset_id,
                                     confirm_prod=confirm_prod, has_execute_prod=has_execute_prod)
    return _do_execute(db, request_def, assertions, environment_id=environment_id,
                       confirm_prod=confirm_prod, has_execute_prod=has_execute_prod)


def quick_execute(
    db: Session,
    request_def: dict,
    *,
    assertions: list[dict] | None = None,
    environment_id: int | None = None,
    dataset_id: int | None = None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
) -> dict:
    """即时执行（不依赖已保存用例），用于调试面板。若提供 dataset_id 则批量执行。"""
    if dataset_id:
        return _execute_with_dataset(db, request_def, assertions or [], environment_id, dataset_id,
                                     confirm_prod=confirm_prod, has_execute_prod=has_execute_prod)
    return _do_execute(db, request_def, assertions or [], environment_id=environment_id,
                       confirm_prod=confirm_prod, has_execute_prod=has_execute_prod)


# ═══════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════

def _do_execute(
    db: Session,
    request_def: dict,
    assertions: list[dict],
    *,
    environment_id: int | None = None,
    dataset_row_index: int | None = None,
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
) -> dict:
    """核心执行流程：解析变量 → 生产保护检查 → 发请求 → 跑断言 → 汇总结果。"""
    method = (request_def.get("method") or "GET").upper()
    url = request_def.get("url") or ""
    headers = request_def.get("headers") or {}
    body = request_def.get("body") or ""

    # 0. 生产环境保护检查
    allowed, prod_msg = _check_prod_protection(db, method, environment_id, confirm_prod, has_execute_prod)
    if not allowed:
        return _error_result(prod_msg)

    # 1. 变量替换
    if environment_id:
        url = resolve_variables(db, environment_id, url)
        body = resolve_variables(db, environment_id, body)
        resolved_headers = {}
        for k, v in headers.items():
            k2 = resolve_variables(db, environment_id, k)
            v2 = resolve_variables(db, environment_id, str(v))
            resolved_headers[k2] = v2
        headers = resolved_headers

    # 2. 解析最终 URL
    resolved_url = _resolve_url(db, environment_id, url)

    # 3. 构建请求快照（执行前）
    request_snapshot = _build_request_snapshot(
        method=method,
        original_url=request_def.get("url", ""),
        resolved_url=resolved_url,
        headers=headers,
        body=body,
        environment_id=environment_id,
        dataset_row_index=dataset_row_index,
    )

    # 4. 发起 HTTP 请求
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            resp = client.request(
                method=method,
                url=resolved_url,
                headers=_prepare_headers(headers, body),
                content=body if method in ("POST", "PUT", "PATCH") else None,
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

    except httpx.TimeoutException:
        return _error_result("请求超时 (30s)", request_snapshot)
    except httpx.ConnectError as e:
        return _error_result(f"连接失败: {e}", request_snapshot)
    except Exception as e:
        return _error_result(f"请求异常: {type(e).__name__}: {e}", request_snapshot)

    # 5. 执行断言
    assertion_results = _run_assertions(
        assertions,
        status_code=resp.status_code,
        response_data=response_data,
        raw_body=raw_body,
        duration_ms=duration_ms,
        response_headers=resp_headers,
    )
    all_pass = all(a["passed"] for a in assertion_results) if assertion_results else True

    # 6. 构建响应快照
    full_body = raw_body if raw_body else ""
    body_size = len(raw_body) if raw_body else 0
    body_truncated = body_size > MAX_RESPONSE_BODY_SIZE
    body_preview = _truncate_for_preview(full_body, BODY_PREVIEW_MAX_SIZE)
    response_snapshot = {
        "status_code": resp.status_code,
        "headers": resp_headers,
        "body_preview": body_preview,
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
        else:
            r = {"type": atype, "expected": rule.get("expected"), "actual": None,
                 "passed": False, "message": f"未知断言类型: {atype}"}
        results.append(r)
    return results


def _assert_status_code(rule: dict, status_code: int) -> dict:
    expected = rule.get("expected", 200)
    op = rule.get("operator", "eq")
    passed = _compare(status_code, expected, op)
    return {
        "type": "status_code",
        "expected": f"{op} {expected}",
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
        "expected": f"{op} {expected}ms",
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
        "expected": f"{op} {expected}",
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
    if op == "eq" or op == "equals":
        return actual == expected
    if op == "neq" or op == "not_equals":
        return actual != expected
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


def _error_result(message: str, request_snapshot: dict | None = None) -> dict:
    return {
        "status": "error",
        "status_code": 0,
        "response_headers": {},
        "response_body": None,
        "raw_body": None,
        "duration_ms": 0,
        "assertions": [],
        "all_pass": False,
        "error": message,
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
    environment_id: int | None = None,
    dataset_row_index: int | None = None,
) -> dict:
    """构建完整请求快照，敏感头脱敏，包含可复制 curl 命令。"""
    safe_headers = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            safe_headers[k] = SENSITIVE_MASK
        else:
            safe_headers[k] = v

    safe_body = body
    if body and len(str(body)) > 10000:
        safe_body = str(body)[:10000] + f"\n... (truncated, total {len(str(body))} bytes)"

    snapshot = {
        "method": method,
        "original_url": original_url,
        "resolved_url": resolved_url,
        "headers": safe_headers,
        "body": safe_body,
        "environment_id": environment_id,
        "dataset_row_index": dataset_row_index,
        "curl": build_curl_command({
            "method": method,
            "resolved_url": resolved_url,
            "original_url": original_url,
            "headers": safe_headers,
            "body": safe_body,
        }),
    }
    return snapshot


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
    if env.env_type != "prod":
        return True, ""

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
    confirm_prod: bool = False,
    has_execute_prod: bool = False,
) -> dict:
    """遍历数据集每一行，逐行替换 ${column_name} 并执行，返回批量结果。"""
    from app.services.dataset_service import get_dataset_rows, get_dataset

    rows = get_dataset_rows(db, dataset_id)
    dataset = get_dataset(db, dataset_id)
    columns = json.loads(dataset["columns_meta"]) if dataset else []

    per_row_results = []
    for row_idx, row in enumerate(rows):
        # Deep-copy request_def to avoid mutation across iterations
        row_req = copy.deepcopy(request_def)
        row_assertions = copy.deepcopy(assertions)

        # Substitute ${column_name} in url, headers, body
        row_req["url"] = _substitute_columns(row_req.get("url", ""), row)
        row_req["body"] = _substitute_columns(row_req.get("body", ""), row)
        headers = row_req.get("headers", {})
        if isinstance(headers, dict):
            for k, v in headers.items():
                headers[k] = _substitute_columns(str(v), row)

        # Execute
        result = _do_execute(db, row_req, row_assertions, environment_id=environment_id,
                            dataset_row_index=row_idx, confirm_prod=confirm_prod,
                            has_execute_prod=has_execute_prod)
        per_row_results.append({
            "row_index": row_idx,
            "row_data": row,
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
