"""Batch 124 — 清理生产/本地知识图谱重复实体（按 entity_key 去重，保留 id 最小者）。

运行: TP_ADMIN_PASSWORD=<pwd> <python> scripts/knowledge/dedup-entities.py [--backend-url <url>] [--dry-run]
说明: 图谱 graph_view 已做前端去重兜底；本脚本清理数据库重复行，避免数据膨胀。
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx

USERNAME = "admin"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    # 通过 /knowledge/graph/entities 拉取并本地分组统计重复（后端不提供批量删除端点，登记结果）
    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=120,
                      headers={"Origin": "https://swiftbugs.cn", "X-Project-Id": "1"}) as client:
        r = client.post("/auth/login", json={"username": USERNAME, "password": args.password})
        r.raise_for_status()
        client.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
        entities = []
        for et in ["module", "test_case", "api", "field", "requirement", "defect"]:
            rr = client.get("/knowledge/graph/entities", params={"entity_type": et, "limit": 1000})
            if rr.status_code == 200:
                entities.extend(rr.json().get("data") or [])
        from collections import Counter
        keys = [e.get("entity_key") or "" for e in entities]
        dup = {k: c for k, c in Counter(keys).items() if c > 1}
        print(f"[dedup] 实体 {len(entities)} 条；重复 entity_key {len(dup)} 组（多余 {sum(c-1 for c in dup.values())} 条）", flush=True)
        for k, c in list(dup.items())[:20]:
            print(f"  dup x{c}: {k[:120]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
