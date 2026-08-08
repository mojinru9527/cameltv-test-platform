# -*- coding: utf-8 -*-
"""体育全模块用例批量入库（Batch 125 / Slice 4，部署后执行）。

读取 module-cases-consolidated.json（基础用例 + 深度用例），通过 POST /test-cases 批量入库。
幂等：按 case_id 查重（已存在跳过）。

用法:
    python scripts/import_sports_cases.py --password <TP_ADMIN_PASSWORD> [--dry-run]
凭据: --password 或环境变量 TP_ADMIN_PASSWORD。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
CONSOLIDATED = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "module-cases-consolidated.json"


def to_create(c: dict, prefix: str) -> dict:
    steps = c.get("steps") or []
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception:
            steps = []
    tags = c.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    steps_payload = []
    for i, s in enumerate(steps, start=1):
        if isinstance(s, dict):
            steps_payload.append({"step": s.get("step") or i, "desc": s.get("desc", ""), "expected": s.get("expected", "")})
        else:
            steps_payload.append({"step": i, "desc": str(s), "expected": ""})
    return {
        "case_id": c.get("case_id") or f"{prefix}-{c.get('id', '')}",
        "title": c.get("title", ""),
        "domain": c.get("domain") or ("体育-运营后台-功能" if "运营后台" in (c.get("module") or "") else "体育-用户端-功能"),
        "module": c.get("module", ""),
        "case_type": c.get("case_type", "manual"),
        "priority": (c.get("priority") or "P2").replace("P", "") if str(c.get("priority") or "").startswith("P") else (c.get("priority") or "P2"),
        "tags": json.dumps(tags, ensure_ascii=False),
        "case_design_method": c.get("case_design_method", ""),
        "positive_negative": c.get("positive_negative", ""),
        "test_data_note": c.get("test_data_note", ""),
        "preconditions": c.get("preconditions", ""),
        "steps": json.dumps(steps_payload, ensure_ascii=False),
        "expected_result": c.get("expected_result", ""),
        "source": "batch-125",
        "source_req_id": c.get("source_doc", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default=os.environ.get("TP_ADMIN_USER", "sportsadmin"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not args.password and not args.dry_run:
        print("缺少 --password", file=sys.stderr)
        return 1
    data = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    print(f"[import] 汇总: {summary}", flush=True)

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": "https://test-platform.up.railway.app"}
    if not args.dry_run:
        with httpx.Client(timeout=120) as client:
            r = client.post(base + "/auth/login", json={"username": args.username, "password": args.password})
            r.raise_for_status()
            j = r.json()
            token = j.get("data", {}).get("access_token") or j.get("access_token", "")
            headers["Authorization"] = f"Bearer {token}"
            rp = client.get(base + "/projects", headers=headers)
            projects = rp.json().get("data", [])
            pid = projects[0]["id"] if projects else 1
            headers["X-Project-Id"] = str(pid)

    total = created = skipped = failed = 0
    with httpx.Client(timeout=120) as client:
        for mod in data["modules"]:
            for c in mod["base"] + mod["deep"]:
                if args.limit and total >= args.limit:
                    break
                total += 1
                payload = to_create(c, "SP-B125")
                if args.dry_run:
                    print(f"[dry-run] POST /test-cases {payload['case_id']} {payload['title'][:30]}", flush=True)
                    created += 1
                    continue
                try:
                    # 幂等：先按 case_id 查
                    q = client.get(base + "/test-cases", params={"case_id": payload["case_id"], "page": 1, "page_size": 1}, headers=headers, timeout=60)
                    exist = q.json().get("data", {}).get("items") or q.json().get("data", {}).get("total", 0)
                    if isinstance(exist, int) and exist > 0:
                        skipped += 1
                        continue
                    if isinstance(exist, list) and exist:
                        skipped += 1
                        continue
                    r = client.post(base + "/test-cases", json=payload, headers=headers, timeout=120)
                    if r.status_code >= 400:
                        print(f"[fail] {payload['case_id']}: {r.status_code} {r.text[:120]}", flush=True)
                        failed += 1
                    else:
                        created += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"[err] {payload['case_id']}: {exc}", flush=True)
                    failed += 1
            if args.limit and total >= args.limit:
                break
            time.sleep(0.2)
    print(f"[import] 完成：total={total} created={created} skipped={skipped} failed={failed}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
