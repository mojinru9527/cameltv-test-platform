"""C120-1 — 交互拓扑全量导入（evidence → 平台 API，幂等）。

运行: <venv-python> test-platform-v2/scripts/import-topology.py [--evidence <json>] [--backend-url <url>]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(Path(__file__).resolve().parents[1] / "work-logs" / "evidence" / "batch-113" / "interaction-paths.json"))
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--source-batch", default="batch-113")
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    payload = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    paths = payload.get("paths") or []
    edges = [
        {
            "from_module": str(p.get("from_module") or ""),
            "entry": str(p.get("entry") or ""),
            "to": str(p.get("to") or ""),
            "evidence": str(p.get("evidence") or ""),
        }
        for p in paths
        if isinstance(p, dict) and p.get("to")
    ]
    print(f"[edges] {len(edges)} 条（evidence {args.evidence}）", flush=True)

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=120,
                      headers={"Origin": "https://swiftbugs.cn", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
        r = c.post("/interaction-coverage/import", json={"edges": edges, "source_batch": args.source_batch})
        r.raise_for_status()
        print("[import]", r.json().get("data"), flush=True)
        r = c.get("/interaction-coverage/topology")
        print("[topology]", r.json().get("data", {}).get("total"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
