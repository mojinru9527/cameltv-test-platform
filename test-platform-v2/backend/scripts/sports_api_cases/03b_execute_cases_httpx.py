# -*- coding: utf-8 -*-
"""Q4 全量执行（httpx keep-alive + 重试）。执行全部用例（含负向+写操作），回填结果。"""
import json, time
import httpx

GW = "http://camel-api-gateway05.svc.elelive.cn"
TIMEOUT = 35.0

def build_assertions_eval(assertions, status, duration_ms, body):
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
            val = resolve_jp(body, a.get("path", ""))
            if op == "eq": ok = val == exp
            elif op == "ne": ok = val != exp
            elif op == "exists": ok = val is not None
        results.append({"assertion": a, "passed": bool(ok)})
    return results

def resolve_jp(body, path):
    if not isinstance(body, dict):
        return None
    cur = body
    for p in path.lstrip("$.").split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

def is_timeout(e):
    s = repr(e).lower()
    return "timed out" in s or "timeout" in s or "timeout (" in s or "10060" in s

def do_req(client, method, url):
    """仅对连接/DNS 错误重试；超时直接返回（诚实记录，不无限等慢接口）。"""
    last_err = None
    for attempt in range(3):
        try:
            t0 = time.time()
            r = client.request(method, url, timeout=TIMEOUT)
            dur = (time.time() - t0) * 1000
            return r.status_code, r.text, dur, None
        except Exception as e:
            last_err = repr(e)[:160]
            if is_timeout(e):
                # 超时：不重试，直接返回（慢接口诚实记录超时）
                return None, "", 0, last_err
            time.sleep(0.5 * (attempt + 1))
    return None, "", 0, last_err

def main():
    data = json.load(open("F:\\CamelTv\\_tmp_cases_generated.json", encoding="utf-8"))
    cases = data["cases"]
    client = httpx.Client(base_url=GW, trust_env=False, limits=httpx.Limits(max_connections=4), timeout=TIMEOUT)
    executed = passed = failed = neterr = 0
    for i, c in enumerate(cases):
        method = c["api_method"]
        endpoint = c["api_endpoint"]
        url = endpoint  # relative to base_url (httpx joins base_url)
        status, body, dur, err = do_req(client, method, url)
        if err:
            c["last_response_json"] = json.dumps({"error": err}, ensure_ascii=False)
            c["last_run_status"] = "failed"
            c["execution"] = {"url": url, "error": err}
            executed += 1; failed += 1; neterr += 1
        else:
            try:
                body_json = json.loads(body) if body.strip() else None
            except Exception:
                body_json = None
            assertions = json.loads(c["api_assertions"])
            results = build_assertions_eval(assertions, status, dur, body_json)
            all_pass = all(r["passed"] for r in results)
            c["last_response_json"] = json.dumps({
                "http_status": status, "duration_ms": round(dur, 1),
                "body": body[:2000], "body_truncated": len(body) > 2000,
            }, ensure_ascii=False)
            c["last_run_status"] = "passed" if all_pass else "failed"
            c["execution"] = {"assertion_results": results, "url": url}
            executed += 1
            if all_pass: passed += 1
            else: failed += 1
        time.sleep(0.1)  # 轻微间隔防限流
        if (i + 1) % 100 == 0:
            print("  progress %d/%d passed=%d failed=%d neterr=%d" % (i + 1, len(cases), passed, failed, neterr))

    data["cases"] = cases
    data["execution_summary"] = {"total": len(cases), "executed": executed, "passed": passed,
                                 "failed": failed, "network_err": neterr}
    with open("F:\\CamelTv\\_tmp_cases_executed.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("=== summary ===")
    print("  total=%d executed=%d passed=%d failed=%d neterr=%d" % (len(cases), executed, passed, failed, neterr))
    client.close()

if __name__ == "__main__":
    main()
