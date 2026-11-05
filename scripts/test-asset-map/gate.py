#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""覆盖率门禁：把标准里的准出线变成 CI 可执行命令。

用法：
    python scripts/test-asset-map/gate.py \
        --summary out/futurewayu/summary.json \
        --assertions web-assertions.csv \
        --min-page-coverage 0.95 \      # 页面清单完整度（有 path 的页面 / 总页面）
        --max-unassigned 0.05 \         # 接口未归类率
        --min-assert-pass 0.90 \        # 可执行断言通过率
        --require-rules R07,R21,R22 \
        --out gate-report.json

退出码：0 通过；1 不通过（CI 直接阻断）。
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--assertions", default="")
    ap.add_argument("--min-page-coverage", type=float, default=0.95)
    ap.add_argument("--max-unassigned", type=float, default=0.05)
    ap.add_argument("--min-assert-pass", type=float, default=0.90)
    ap.add_argument("--require-rules", default="")
    ap.add_argument("--out", default="gate-report.json")
    args = ap.parse_args()

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    checks = []

    pages = summary.get("pages", 0)
    with_path = summary.get("pages_with_path", pages)
    page_cov = with_path / max(1, pages)
    checks.append({"name": "page_inventory_coverage", "value": round(page_cov, 3),
                   "threshold": args.min_page_coverage, "pass": page_cov >= args.min_page_coverage,
                   "detail": f"{with_path}/{pages} 页面有可访问路径"})

    endpoints = summary.get("endpoints", 0)
    unassigned = len(summary.get("unassigned_endpoints") or [])
    ratio = unassigned / max(1, endpoints)
    checks.append({"name": "endpoint_assignment", "value": round(ratio, 4),
                   "threshold": args.max_unassigned, "pass": ratio <= args.max_unassigned,
                   "detail": f"未归类 {unassigned}/{endpoints}"})

    if args.assertions:
        rows = read_csv(args.assertions)
        total = [r for r in rows if r["status"] in ("PASS", "FAIL")]
        passed = [r for r in rows if r["status"] == "PASS"]
        rate = len(passed) / max(1, len(total))
        checks.append({"name": "assertion_pass_rate", "value": round(rate, 3),
                       "threshold": args.min_assert_pass, "pass": rate >= args.min_assert_pass,
                       "detail": f"PASS {len(passed)}/{len(total)}，BLOCKED "
                                 f"{len([r for r in rows if r['status'] == 'BLOCKED'])}"})
        if args.require_rules:
            have = {r["rule_id"] for r in rows}
            missing = [x for x in args.require_rules.split(",") if x.strip() and x.strip() not in have]
            checks.append({"name": "required_rules_measured", "value": len(have),
                           "threshold": len(have) + len(missing), "pass": not missing,
                           "detail": f"缺失规则断言: {missing}"})
        # 失败明细（便于 CI 直接定位）
        failures = [r for r in rows if r["status"] == "FAIL"][:10]
    else:
        failures = []

    ok = all(c["pass"] for c in checks)
    report = {"project": summary.get("project"), "pass": ok, "checks": checks, "sample_failures": failures}
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"gate: {'PASS' if ok else 'FAIL'}")
    for c in checks:
        print(f"  [{'ok' if c['pass'] else 'NG'}] {c['name']}: {c['value']} (阈值 {c['threshold']}) {c['detail']}")
    for f in failures[:5]:
        print(f"    FAIL {f['rule_id']} {f['page']} {f.get('metric','')} {f.get('evidence','')[:80]}")
    print(f"report -> {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
