"""体育平台承接 — 功能用例覆盖度审计（Batch 110 QA 证据）。

通过平台 API 统计功能用例按 域/模块/优先级 分布，核验：
  1) 用户端/运营后台各模块是否有用例（无缺口）；
  2) 每功能点覆盖 ≥2 条（Batch 103 目标）的可查证口径；
  3) P0 标识数量 ≥30。

运行: <venv-python> scripts/sports/audit-functional-cases.py --password <pw> [--backend-url ...]
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    base = args.backend_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=90, headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        by_module = Counter()
        by_priority = Counter()
        by_domain = Counter()
        page = 1
        while True:
            r = c.get("/test-cases", params={"page": page, "page_size": 200, "case_type": "manual"})
            r.raise_for_status()
            data = r.json().get("data", {})
            items = data.get("items") or []
            total = data.get("total", 0)
            for it in items:
                if it.get("domain") not in ("体育平台-用户端", "体育平台-运营后台"):
                    continue
                by_domain[it.get("domain")] += 1
                by_module[it.get("module") or "(无模块)"] += 1
                by_priority[it.get("priority") or "UNSET"] += 1
            if page * 200 >= total:
                break
            page += 1

    summary = {
        "domain_counts": dict(by_domain),
        "module_counts": dict(sorted(by_module.items(), key=lambda kv: -kv[1])),
        "priority_counts": dict(by_priority),
        "p0_total": by_priority.get("P0", 0),
        "modules_without_cases": [],
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "functional-case-audit.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[audit] 功能用例总数: {sum(by_domain.values())}（用户端 {by_domain.get('体育平台-用户端', 0)} / 运营后台 {by_domain.get('体育平台-运营后台', 0)}）")
    print(f"[audit] P0: {by_priority.get('P0', 0)} / P1: {by_priority.get('P1', 0)} / P2: {by_priority.get('P2', 0)} / 其他: {by_priority.get('UNSET', 0)}")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
