# -*- coding: utf-8 -*-
"""Batch 132 — 全量用例入图生产脚本（C125-3/C126-1 执行入口）。

登录后调用 POST /api/v1/knowledge/graph/sync-test-cases，将项目全部 active 用例
同步为图谱用例实体并回填来源，能关联模块的建立 tested_by。幂等，可重复执行。

用法:
    python scripts/sync_all_test_cases_to_graph.py [--backend-url URL] [--project-id N] [--username U]
                                                  [--password P]
凭据: --password 或环境变量 TP_ADMIN_PASSWORD。
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="全量用例入图（Batch 132）")
    parser.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    parser.add_argument("--project-id", type=int, default=None, help="指定项目；缺省用第一个项目")
    args = parser.parse_args()

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": base}
    with httpx.Client(timeout=180) as client:
        r = client.post(base + "/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        j = r.json()
        token = j.get("data", {}).get("access_token") or j.get("access_token", "")
        if not token:
            print("[err] 登录失败：未获取 access_token", flush=True)
            return 1
        headers["Authorization"] = f"Bearer {token}"

        if args.project_id:
            pid = args.project_id
        else:
            rp = client.get(base + "/projects", headers=headers)
            rp.raise_for_status()
            projects = rp.json().get("data", [])
            if not projects:
                print("[err] 无可用项目", flush=True)
                return 1
            pid = projects[0]["id"]

        headers["X-Project-Id"] = str(pid)
        rs = client.post(base + "/knowledge/graph/sync-test-cases", headers=headers)
        rs.raise_for_status()
        result = rs.json().get("data", {})
        print(f"[ok] project#{pid} 全量用例入图完成: {result}", flush=True)
        expected = result.get("test_case_entities")
        total = result.get("total_cases")
        if expected is not None and total is not None and expected != total:
            print(f"[warn] 实体数 {expected} 与用例全量 {total} 不一致", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
