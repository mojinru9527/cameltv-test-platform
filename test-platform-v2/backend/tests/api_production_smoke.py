"""
CamelTv 生产环境 API 冒烟测试
目标: https://www.camel1.tv/
测试核心 API 端点可达性
"""
import json
import re
import sys
import time
import httpx

SITE_URL = "https://www.camel1.tv"
TIMEOUT = 30

API_TESTS = [
    ("API-001: 首页", "GET", "/", 200, [("status_code", 200)]),
    ("API-002: 匿名登录", "POST", "/api/account-service/login/anonymous/web", 200, [("status_code", 200)]),
    ("API-003: 赛事列表", "GET", "/api/match-service/match/list", 200, [("status_code", 200)]),
    ("API-004: 直播列表", "GET", "/api/live-service/live/list", 200, [("status_code", 200)]),
    ("API-005: Banner", "GET", "/api/ads-service/ads/list", 200, [("status_code", 200)]),
    ("API-006: 用户协议", "GET", "/api/common-service/agreement/list", 200, [("status_code", 200)]),
    ("API-007: 体育分类", "GET", "/api/match-service/sport/types", 200, [("status_code", 200)]),
    ("API-008: 发送验证码", "POST", "/api/account-service/send-sms-code/web", 200, [("status_code", 200)]),
]


def run_all():
    results = []
    start = time.perf_counter()

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for name, method, path, expected_status, assertions in API_TESTS:
            url = f"{SITE_URL}{path}"
            t0 = time.perf_counter()
            try:
                if method == "GET":
                    resp = client.get(url)
                else:
                    resp = client.post(url, json={})
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                status_ok = resp.status_code == expected_status
                error = None
            except Exception as e:
                duration_ms = 0
                status_ok = False
                error = f"{type(e).__name__}: {e}"

            all_pass = status_ok and error is None
            status = "✅ PASS" if all_pass else f"❌ FAIL"
            print(f"  {status} {name} ({duration_ms}ms)" + (f" [{error}]" if error else ""))

            results.append({
                "name": name, "method": method, "url": url,
                "duration_ms": duration_ms, "all_pass": all_pass,
                "error": error,
            })

    total_time = round(time.perf_counter() - start, 1)
    passed = sum(1 for r in results if r["all_pass"])
    failed = len(results) - passed

    print(f"\n{'='*60}")
    print(f"结果: {passed}/{len(results)} 通过, {failed} 失败 ({total_time}s)")
    print(f"{'='*60}")

    # Save
    output = {
        "test_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "site_url": SITE_URL,
        "total": len(results), "passed": passed, "failed": failed,
        "results": results,
    }
    path = "f:/CamelTv/test-platform-v2/backend/storage/api-test-results-prod.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"结果: {path}")
    return output


if __name__ == "__main__":
    print(f"CamelTv API 生产测试 - {SITE_URL}")
    print(f"测试数: {len(API_TESTS)}\n")
    run_all()
