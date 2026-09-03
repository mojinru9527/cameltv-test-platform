"""VersionTask 执行服务（B8 修复 / F-02）。

用**真实 HTTP 调用**执行带 ``exec_meta`` 的已采纳方案条目：
- ``exec_meta.url`` 直接作为完整目标；
- ``exec_meta.path`` + 任务环境 ``base_url`` 拼成完整目标；
- 无目标 URL 的条目标记为 ``not_run``（**绝不臆造 PASS/FAIL**）——与旧 mock 版 contrast。

产出：真实请求/响应脱敏证据 + 断言结果（通过/失败/未执行），失败分类为 business/script/environment。
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.version_task_plan import VersionTaskPlanItem

_JSONPATH_SEG = re.compile(r"^([^\[\]]+)(?:\[(\d+)\])?$")


def _dig(node: Any, path: str) -> Any:
    cur = node
    for seg in (path or "").split("."):
        if not seg:
            continue
        m = _JSONPATH_SEG.match(seg)
        key = m.group(1) if m else seg
        idx = int(m.group(2)) if m and m.group(2) else None
        if isinstance(cur, dict):
            if key not in cur:
                return None
            cur = cur[key]
        elif isinstance(cur, list) and idx is not None:
            cur = cur[idx] if idx < len(cur) else None
        else:
            return None
        if idx is not None and isinstance(cur, list):
            cur = cur[idx] if idx < len(cur) else None
    return cur


def _compare(actual: Any, op: str, expected: Any) -> bool:
    op = (op or "equals").lower()
    if op in ("equals", "eq"):
        return actual == expected
    if op in ("ne", "not_equals", "ne"):
        return actual != expected
    if op == "exists":
        return (expected is True and actual is not None) or (expected is False and actual is None)
    if op == "contains":
        try:
            return expected in (actual or "")
        except TypeError:
            return False
    if op == "gt":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if op == "gte":
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    return False


def _eval_asserts(meta: dict[str, Any], status: int, body: Any) -> list[dict[str, Any]]:
    """逐条执行 ``assert``（如 [{"type":"status","expected":200},
    {"type":"json","path":"data.ok","op":"equals","expected":true}]）。"""
    results: list[dict[str, Any]] = []
    for a in meta.get("assert") or []:
        a = a or {}
        atype = str(a.get("type") or "")
        expected = a.get("expected")
        ok = False
        if atype == "status":
            ok = int(status) == int(expected)
        elif atype == "json":
            path = str(a.get("path") or "")
            ok = _compare(_dig(body, path), str(a.get("op") or "equals"), expected)
        elif atype == "contains":
            try:
                ok = str(expected) in (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False))
            except (TypeError, ValueError):
                ok = False
        results.append({"type": atype, "path": a.get("path", ""), "expected": expected, "ok": bool(ok)})
    return results


def resolve_base_url(db: Session, task: Any) -> str:
    """由任务解析被测系统 base_url：优先关联环境，其次任务 scope.base_url；无则空串。"""
    if not task:
        return ""
    environment_id = getattr(task, "environment_id", None)
    if environment_id:
        from app.models.environment import Environment as Env

        env = db.get(Env, environment_id)
        if env and env.base_url:
            return str(env.base_url)
    scope = getattr(task, "scope", "") or "{}"
    try:
        parsed = json.loads(scope) if isinstance(scope, str) else (scope or {})
        if isinstance(parsed, dict) and parsed.get("base_url"):
            return str(parsed["base_url"])
    except (TypeError, ValueError):
        return ""
    return ""


def execute_item(db: Session, item: VersionTaskPlanItem, base_url: str) -> dict[str, Any]:
    """执行单个方案条目。返回 with status/pub evidence / failure / not_run 原因。"""
    try:
        meta = json.loads(item.exec_meta or "{}")
    except (TypeError, ValueError):
        meta = {}
    if not isinstance(meta, dict):
        meta = {}

    method = str(meta.get("method") or "GET").upper()
    url = str(meta.get("url") or "").strip()
    path = str(meta.get("path") or "").strip()
    if not url and path:
        if base_url:
            url = base_url.rstrip("/") + (path if path.startswith("/") else "/" + path)
    if not url:
        return {
            "status": "not_run", "reason": "无可执行目标 URL（或未配置被测环境地址）",
            "evidence": [], "failure": None,
        }

    headers = dict(meta.get("headers") or {})
    body = meta.get("body")
    import httpx

    req_snapshot: dict[str, Any] = {"method": method, "url": url, "headers": dict(headers), "body": body}
    status = None
    resp_body: Any = None
    error: str | None = None
    try:
        with httpx.Client(trust_env=False, verify=True, timeout=20) as client:
            resp = client.request(
                method, url, headers=headers, json=body if body is not None else None
            )
            status = resp.status_code
            try:
                resp_body = resp.json()
            except Exception:  # noqa: BLE001
                resp_body = resp.text[:2000]
    except Exception as exc:  # noqa: BLE001
        error = repr(exc)[:300]

    assert_results = [] if error is None and status is not None else None
    if error is None and status is not None:
        assert_results = _eval_asserts(meta, status, resp_body)
    # 无断言时，以可观测状态为唯一标准（2xx 视为健康可达，否则记失败）
    if error is None and status is not None and not assert_results:
        assert_results = [{"type": "status", "expected": 200, "ok": 200 <= status < 300}]

    if error is not None:
        run_status = "fail"
        failure = {"kind": "environment", "message": f"请求失败：{error}"}
    elif assert_results and not all(r["ok"] for r in assert_results):
        run_status = "fail"
        failed = [r for r in assert_results if not r["ok"]]
        failure = {"kind": "business", "message": f"{item.title} 断言失败：{failed}"}
    else:
        run_status = "pass"
        failure = None

    # 脱敏证据（复用 AITDE snapshot_sanitizer；失败时不再额外落敏感头）
    evidence = []
    try:
        from app.modules.aitde.evidence.snapshot_sanitizer import snapshot_sanitizer

        req_clean = snapshot_sanitizer.sanitize_http_snapshot(
            method=method, url=url, headers=headers, params=meta.get("params") or {}, body=body
        )
        resp_clean = snapshot_sanitizer.sanitize_response_snapshot(
            status=status if status is not None else 0, body=resp_body
        )
        evidence = [
            {"type": "REQUEST", "ref": f"item:{item.id}", "status": run_status, "snapshot": req_clean},
            {"type": "RESPONSE", "ref": f"item:{item.id}", "status": run_status, "snapshot": resp_clean},
        ]
    except Exception:  # noqa: BLE001
        evidence = []

    return {
        "status": run_status, "reason": None, "evidence": evidence, "failure": failure,
        "http_status": status, "asserts": assert_results or [], "error": error,
    }
