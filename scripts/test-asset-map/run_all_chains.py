#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量执行链路（按 manifest 过滤就绪等级），聚合结果。

用法：
    python scripts/test-asset-map/run_all_chains.py \
        --manifest docs/standards/project-adapters/chains/futurewayu/manifest.json \
        --env runtime/env.json --out-dir runtime/chains \
        --statuses ready,ready-readonly --spacing-ms 200
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--statuses", default="ready,ready-readonly")
    ap.add_argument("--spacing-ms", type=int, default=200)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    base = Path(args.manifest).parent
    wanted = {s.strip() for s in args.statuses.split(",") if s.strip()}
    targets = [c for c in manifest["chains"] if c.get("status") in wanted]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    t0 = time.time()
    for ch in targets:
        spec = base / ch["file"]
        out = out_dir / f"{ch['chain_id']}.csv"
        r = subprocess.run([sys.executable, str(HERE / "run_chain.py"),
                            "--spec", str(spec), "--env", args.env, "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        verdict = {}
        vp = out.with_suffix(".verdict.json")
        if vp.exists():
            verdict = json.loads(vp.read_text(encoding="utf-8"))
        status = verdict.get("status", "ERROR")
        steps = verdict.get("steps") or []
        passed = sum(1 for s in steps if s.get("status") == "PASS")
        failed = [s for s in steps if s.get("status") not in ("PASS", None)]
        rows.append({"chain_id": ch["chain_id"], "domain": ch["domain"],
                     "priority": ch.get("priority"), "spec_status": ch.get("status"),
                     "result": status, "steps": len(steps), "passed": passed,
                     "failed": len(failed), "failed_detail": json.dumps(failed, ensure_ascii=False)[:2000]})
        print(f"[{status:7s}] {ch['chain_id'][:46]:46s} {passed}/{len(steps)}")
        time.sleep(args.spacing_ms / 1000.0)

    out_csv = out_dir / "summary.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["chain_id"])
        w.writeheader()
        w.writerows(rows)

    stat = Counter(r["result"] for r in rows)
    total_steps = sum(r["steps"] for r in rows)
    total_pass = sum(r["passed"] for r in rows)
    print(f"\nchains={len(rows)} results={dict(stat)} steps={total_pass}/{total_steps} "
          f"({round(100*total_pass/max(1,total_steps),1)}%) {int(time.time()-t0)}s")
    print(f"-> {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
