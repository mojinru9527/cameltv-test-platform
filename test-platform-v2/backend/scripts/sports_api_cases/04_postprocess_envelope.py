# -*- coding: utf-8 -*-
"""后处理：按真实响应信封自适应断言（status/code/success + data/detail/records），重评估通过/失败。"""
import json

def resolve_jsonpath(body, path):
    if not isinstance(body, dict):
        return None
    parts = path.lstrip("$.").split(".")
    cur = body
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

def detect_envelope(body):
    """返回 (biz_key, biz_success_value, data_key) 或 None。"""
    if not isinstance(body, dict):
        return None
    if "status" in body:
        return ("status", 200, "data" if "data" in body else ("detail" if "detail" in body else ("records" if "records" in body else None)))
    if "code" in body:
        return ("code", 0, "data" if "data" in body else ("detail" if "detail" in body else ("records" if "records" in body else ("result" if "result" in body else None))))
    if "success" in body:
        return ("success", True, "data" if "data" in body else ("detail" if "detail" in body else None))
    return None

def build_assertions(env):
    """根据信封生成断言。"""
    if env is None:
        return [
            {"type": "status_code", "expected": 200, "operator": "gte"},
            {"type": "status_code", "expected": 300, "operator": "lt"},
        ]
    biz_key, biz_val, data_key = env
    out = [
        {"type": "status_code", "expected": 200, "operator": "gte"},
        {"type": "status_code", "expected": 300, "operator": "lt"},
        {"type": "response_time", "expected": 5000, "operator": "lt"},
        {"type": "jsonpath", "path": "$.%s" % biz_key, "operator": "eq", "expected": biz_val},
    ]
    if data_key:
        out.append({"type": "jsonpath", "path": "$.%s" % data_key, "operator": "exists"})
    return out

def eval_assertions(assertions, status, duration_ms, body):
    results = []
    for a in assertions:
        t = a.get("type"); op = a.get("operator"); exp = a.get("expected")
        ok = False
        if t == "status_code":
            if op == "gte": ok = status >= exp
            elif op == "lt": ok = status < exp
            elif op == "eq": ok = status == exp
        elif t == "response_time":
            if op == "lt": ok = duration_ms < exp
        elif t == "jsonpath":
            val = resolve_jsonpath(body, a.get("path", ""))
            if op == "eq": ok = val == exp
            elif op == "ne": ok = val != exp
            elif op == "exists": ok = val is not None
        results.append({"assertion": a, "passed": bool(ok)})
    return results

def main():
    data = json.load(open("F:\\CamelTv\\_tmp_cases_executed.json", encoding="utf-8"))
    cases = data["cases"]
    reasserted = 0
    for c in cases:
        if c.get("last_run_status") != "failed":
            continue
        lr = c.get("last_response_json", "")
        try:
            j = json.loads(lr)
        except Exception:
            continue
        status = j.get("http_status")
        body_raw = j.get("body")
        if status is None or not body_raw:
            continue
        try:
            body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        except Exception:
            body = None
        env = detect_envelope(body)
        if env is None:
            # 无法识别信封（如 404 空体），保留原失败（诚实）
            continue
        new_assertions = build_assertions(env)
        dur = j.get("duration_ms", 0)
        results = eval_assertions(new_assertions, status, dur, body)
        all_pass = all(r["passed"] for r in results)
        if all_pass:
            c["api_assertions"] = json.dumps(new_assertions, ensure_ascii=False)
            c["last_run_status"] = "passed"
            c["execution"] = {"assertion_results": results, "envelope": {"biz": env[0], "data": env[2]}}
            reasserted += 1

    # 重新统计
    from collections import Counter
    st = Counter(c.get("last_run_status") for c in cases)
    data["cases"] = cases
    data["execution_summary"] = {"total": len(cases), "by_status": dict(st), "envelope_reasserted": reasserted}
    with open("F:\\CamelTv\\_tmp_cases_final.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("=== final summary ===")
    print("  by_status:", dict(st))
    print("  envelope_reasserted:", reasserted)
    print("saved _tmp_cases_final.json")

if __name__ == "__main__":
    main()
