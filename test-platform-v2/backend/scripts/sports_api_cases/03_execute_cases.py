# -*- coding: utf-8 -*-
"""真实执行正向用例（只读 GET + 安全读 POST），回填 last_response_json + last_run_status。

写操作（save/delete/bet/settle/stop_push 等）不执行，标记 last_run_status='pending'
并注明「写操作，需单独授权执行」。
"""
import json, urllib.request, ssl, time

GW = "http://camel-api-gateway05.svc.elelive.cn"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

# 副作用 GET 明确黑名单（刷新/同步/清空/关闭/初始化/测试推送）
SIDE_EFFECT_GET = [
    "/refreshAllNode", "/sync_team", "/sync_competition", "/reHandleMatchLineup",
    "/syncSeasonPlayer", "/syncPlayerSeasonStat", "/syncNationalPlayer",
    "/redis/clear", "/closeHalfAds", "/fifa/sync/matchOdds",
    "/activity/market_value_change/init", "/test/matchpush",
]

def is_skip(method, path):
    """返回 True 表示不执行（写操作/副作用）。仅执行只读 GET。"""
    if method != "GET":
        return True  # 所有 POST 不执行（写/动作，需单独授权）
    p = path.lower()
    return any(k.lower() in p for k in SIDE_EFFECT_GET)

def get(url, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent": "camel-qa", "Accept": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status, r.read().decode("utf-8", "replace"), (time.time() - t0) * 1000

def eval_assertions(assertions, status, duration_ms, body_json):
    results = []
    for a in assertions:
        t = a.get("type")
        op = a.get("operator")
        exp = a.get("expected")
        ok = False
        if t == "status_code":
            if op == "gte":
                ok = status >= exp
            elif op == "lt":
                ok = status < exp
            elif op == "eq":
                ok = status == exp
        elif t == "response_time":
            if op == "lt":
                ok = duration_ms < exp
        elif t == "jsonpath":
            path = a.get("path", "")
            # 简单 jsonpath: $.status, $.data, $.data.X
            val = resolve_jsonpath(body_json, path)
            if op == "eq":
                ok = val == exp
            elif op == "ne":
                ok = val != exp
            elif op == "exists":
                ok = val is not None
        results.append({"assertion": a, "passed": bool(ok), "actual_status": status})
    return results

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

def main():
    data = json.load(open("F:\\CamelTv\\_tmp_cases_generated.json", encoding="utf-8"))
    cases = data["cases"]
    executed = 0; passed = 0; failed = 0; pending = 0; network_err = 0
    for i, c in enumerate(cases):
        method = c["api_method"]
        endpoint = c["api_endpoint"]  # /svc/ee/... 已带前缀
        pn = c["positive_negative"]
        # 只执行正向用例；负向用例仅对 GET 执行（写 POST 负向也跳过）
        if pn != "positive":
            c["last_run_status"] = "pending"
            c["last_response_json"] = ""
            pending += 1
            continue
        # 写操作/副作用跳过
        if is_skip(method, endpoint):
            c["last_run_status"] = "pending"
            c["last_response_json"] = ""
            c["test_data_note"] = (c["test_data_note"] + " 执行说明：写操作/副作用接口，需单独授权执行（本批未执行）。")
            pending += 1
            continue
        # 真实执行
        url = GW + endpoint
        try:
            status, body, dur = get(url)
            try:
                body_json = json.loads(body)
            except Exception:
                body_json = None
            assertions = json.loads(c["api_assertions"])
            results = eval_assertions(assertions, status, dur, body_json)
            all_pass = all(r["passed"] for r in results)
            c["last_response_json"] = json.dumps({
                "http_status": status,
                "duration_ms": round(dur, 1),
                "body": body[:2000],
                "body_truncated": len(body) > 2000,
            }, ensure_ascii=False)
            c["last_run_status"] = "passed" if all_pass else "failed"
            c["execution"] = {"assertion_results": results, "url": url}
            executed += 1
            if all_pass:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            c["last_response_json"] = json.dumps({"error": repr(e)[:200]}, ensure_ascii=False)
            c["last_run_status"] = "failed"
            c["execution"] = {"url": url, "error": repr(e)[:200]}
            executed += 1
            failed += 1
            network_err += 1
        if (i + 1) % 50 == 0:
            print("  progress %d/%d (passed=%d failed=%d pending=%d)" % (i + 1, len(cases), passed, failed, pending))

    data["cases"] = cases
    data["execution_summary"] = {
        "total_cases": len(cases),
        "executed": executed, "passed": passed, "failed": failed, "pending": pending,
        "network_err": network_err,
    }
    with open("F:\\CamelTv\\_tmp_cases_executed.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("=== execution summary ===")
    print("  total=%d executed=%d passed=%d failed=%d pending=%d network_err=%d" % (
        len(cases), executed, passed, failed, pending, network_err))
    print("saved _tmp_cases_executed.json")

if __name__ == "__main__":
    main()
