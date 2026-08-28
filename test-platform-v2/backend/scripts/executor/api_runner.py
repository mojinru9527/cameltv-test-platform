#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""内网 API 执行器（Runner）— 跑在「能连内网/VPN」的机器上。

用途：平台（swiftbugs.cn 公网）不可直达纯内网 API（如 camel-api-gateway05.svc.elelive.cn，
解析到 192.168.50.170）。internal 环境 + execution_mode=runner 时，平台派发任务给本 runner，
由本脚本在 VPN 机上实际执行 + 回传结果。

用法（在能连内网的机器 + 设置环境变量）：
    PLATFORM_URL=https://swiftbugs.cn
    API_USERNAME=<平台账号>          # 如 sportsadmin
    API_PASSWORD=<平台密码>
    RUNNER_KEY=test5-internal-01     # 与执行环境 runner_key 匹配
    PROJECT_ID=1
    python scripts/executor/api_runner.py --once   # 认领并执行一条（测试）；不带 --once 则循环

Batch 206 / C-内网执行器。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx

PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://swiftbugs.cn").rstrip("/")
USERNAME = os.environ.get("API_USERNAME", "")
PASSWORD = os.environ.get("API_PASSWORD", "")
RUNNER_KEY = os.environ.get("RUNNER_KEY", "test5-internal-01")
PROJECT_ID = os.environ.get("PROJECT_ID", "1")
POLL_SECONDS = float(os.environ.get("RUNNER_POLL_SECONDS", "5"))


def login() -> str:
    c = httpx.Client(base_url=PLATFORM_URL, trust_env=False, timeout=30, follow_redirects=True)
    r = c.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    if r.status_code != 200:
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:150]}")
    return r.json()["data"]["access_token"]


def claim(client: httpx.Client) -> dict | None:
    r = client.post("/api/v1/apitest/runner/claim", json={"runner_key": RUNNER_KEY})
    try:
        d = r.json().get("data")
    except Exception:
        d = None
    return d if d and d.get("claimed") else None


def execute_request(env_base: str, req: dict) -> tuple[int, str, float]:
    """真正发起 HTTP 请求（在 VPN 机上执行）。"""
    # req: {method, url, headers, body, query_params}
    method = (req.get("method") or "GET").upper()
    url = req.get("url") or ""
    if not url.startswith("http"):
        url = env_base.rstrip("/") + "/" + url.lstrip("/")
    headers = req.get("headers") or {}
    body = req.get("body") or ""
    qp = req.get("query_params") or {}
    t0 = time.time()
    with httpx.Client(trust_env=False, timeout=90, follow_redirects=False) as client:
        r = client.request(method, url, headers=headers, params=qp,
                           json=json.loads(body) if body and body.startswith(("{", "[")) else (body or None))
        return r.status_code, r.text, (time.time() - t0) * 1000


def evaluate_assertions(result: dict, assertions: list[dict]) -> tuple[bool, list[dict]]:
    """简单断言求值（与平台 _do_execute 同构：status_code/jsonpath/response_time）。"""
    status, body, dur = result.get("http_status"), result.get("body"), result.get("duration_ms")
    try:
        parsed = json.loads(body) if body else None
    except Exception:
        parsed = None

    def jp(obj, path: str):
        if not isinstance(obj, dict):
            return None
        cur = obj
        for p in path.lstrip("$.").split("."):
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return None
        return cur

    outcomes = []
    for a in assertions:
        t, op, exp = a.get("type"), a.get("operator"), a.get("expected")
        ok = False
        if t == "status_code":
            ok = {"gte": status >= exp, "lt": status < exp, "eq": status == exp}.get(op, False)
        elif t == "response_time":
            ok = dur < exp if op == "lt" else False
        elif t == "jsonpath":
            val = jp(parsed, a.get("path", ""))
            ok = {"eq": val == exp, "ne": val != exp, "exists": val is not None}.get(op, False)
        outcomes.append({"assertion": a, "passed": bool(ok)})
    return all(o["passed"] for o in outcomes), outcomes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="认领并执行一条后退出")
    args = parser.parse_args()

    if not (USERNAME and PASSWORD):
        print("需设置 API_USERNAME / API_PASSWORD / RUNNER_KEY", file=sys.stderr)
        return 2

    client = httpx.Client(base_url=PLATFORM_URL, trust_env=False, timeout=30, follow_redirects=True)
    client.headers.update({"Authorization": "Bearer " + login(), "X-Project-Id": PROJECT_ID})
    print(f"runner[{RUNNER_KEY}] 已连 {PLATFORM_URL}", flush=True)

    processed = 0
    while True:
        task = claim(client)
        if not task:
            if args.once:
                print("无待认领任务", flush=True)
                break
            time.sleep(POLL_SECONDS)
            continue
        tid = task["task_id"]; exec_id = task["execution_id"]
        print(f"  [claim] 任务#{tid} exec={exec_id} env={task['environment_id']} {task['request'].get('method')} {task['request'].get('url','')[:60]}", flush=True)
        # 执行（env base_url 由 runner 侧从环境读取；这里用平台派发的 url，若为相对则需 runner 侧 base）
        req = task["request"]
        env_base = os.environ.get("RUNNER_BASE_URL", "")  # runner 侧配置该内网网关 base
        try:
            status, body, dur = execute_request(env_base, req)
            result = {"http_status": status, "body": body[:2000], "duration_ms": round(dur, 1)}
            all_pass, outcomes = evaluate_assertions({
                "http_status": status, "body": body, "duration_ms": round(dur, 1),
            }, task.get("assertions", []))
            report_status = "done" if all_pass else "failed"
            report_result = {"status": "passed" if all_pass else "failed", "http_status": status,
                             "duration_ms": round(dur, 1), "body": body[:2000],
                             "assertion_results": outcomes}
            client.post("/api/v1/apitest/runner/report",
                        json={"task_id": tid, "status": report_status, "result": report_result})
            print(f"  [done] 任务#{tid} -> HTTP {status} ({round(dur,1)}ms) all_pass={all_pass}", flush=True)
        except Exception as e:
            client.post("/api/v1/apitest/runner/report",
                        json={"task_id": tid, "status": "failed", "result": {}, "error_message": repr(e)[:500]})
            print(f"  [fail] 任务#{tid} -> {repr(e)[:120]}", flush=True)
        processed += 1
        if args.once:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
