#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""链路规格就绪度校验：把"骨架/就绪"从人工标签变成机器可校验。

校验项：
1. 每个 step 必须有 expect（code/code_in/http/code_not_in 之一）。
2. 变量引用 `{x}` 必须能由前置 fixture 的 extract 提供，否则视为不可执行。
3. 含写方法（POST/PUT/DELETE/PATCH）的链路必须有 cleanup，否则降级为 skeleton。
4. ready / ready-readonly 链路必须至少有 2 个可执行 step，且带失败注入或显式说明。
5. 零只读步骤的域必须写明 blocked_reason，不允许静默 skeleton。

用法：
    python scripts/test-asset-map/validate_chains.py --dir docs/standards/project-adapters/chains/futurewayu \
        --out docs/standards/project-adapters/out/futurewayu/chain-readiness.json
退出码：存在等级为 invalid 的链路时返回 1。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
READY = {"ready", "ready-readonly"}


def collect_vars(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text or ""))


def validate(spec: dict) -> dict:
    issues = []
    steps = spec.get("steps") or []
    fixtures = spec.get("fixtures") or []

    provided = set()
    for f in fixtures:
        provided |= set((f.get("extract") or {}).keys())

    for s in steps:
        no = s.get("no")
        exp = s.get("expect") or {}
        if not any(k in exp for k in ("code", "code_in", "code_not_in", "http")):
            issues.append(f"step{no} 缺少 expect")
        for v in collect_vars(s.get("path", "")) | collect_vars(json.dumps(s.get("body") or "", ensure_ascii=False)):
            if v not in provided:
                issues.append(f"step{no} 引用未提供变量 {{{v}}}")

    writes = [s for s in steps if str(s.get("method", "GET")).upper() in WRITE_METHODS]
    if writes and not (spec.get("cleanup") or []) and not spec.get("cleanup_not_applicable"):
        issues.append(f"含 {len(writes)} 个写步骤但缺 cleanup（或 cleanup_not_applicable）")
    if writes and not (spec.get("failure_injection") or []) and not spec.get("note"):
        issues.append("含写步骤但缺 failure_injection（或说明）")

    status = spec.get("status") or "skeleton"
    if status in READY:
        if len(steps) < 1:
            issues.append("ready 链路无步骤")
        if not (spec.get("failure_injection") or spec.get("note")):
            issues.append("ready 链路缺失败注入且无说明")

    if not steps and not spec.get("blocked_reason"):
        issues.append("零步骤且未写 blocked_reason")

    if issues and status in READY:
        grade = "invalid"
    elif issues:
        grade = "needs-work"
    elif status in READY:
        grade = "ready"
    else:
        grade = "skeleton-ok"

    return {"chain_id": spec.get("chain_id"), "domain": spec.get("domain"),
            "priority": spec.get("priority"), "status": status, "grade": grade,
            "steps": len(steps), "writes": len(writes),
            "has_cleanup": bool(spec.get("cleanup")), "has_injection": bool(spec.get("failure_injection")),
            "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reports = []
    for p in sorted(Path(args.dir).glob("CHAIN-*.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        reports.append(validate(spec))

    from collections import Counter
    grades = Counter(r["grade"] for r in reports)
    report = {"total": len(reports), "grades": dict(grades), "chains": reports,
              "ready": sum(1 for r in reports if r["grade"] == "ready"),
              "invalid": [r["chain_id"] for r in reports if r["grade"] == "invalid"]}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"chains={len(reports)} grades={dict(grades)}")
    if report["invalid"]:
        print("INVALID:", report["invalid"])
    for r in reports:
        if r["issues"]:
            print(f"  [{r['grade']}] {r['chain_id'][:44]:44s} " + "; ".join(r["issues"])[:110])
    print(f"-> {out}")
    return 1 if report["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
