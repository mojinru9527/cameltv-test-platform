#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力矩阵：把「页面/链路」与「环境能力」对齐，算出可执行率与阻塞原因。

输入：能力声明 YAML + 页面清单 + 链路 manifest
输出：capability-matrix.json（逐页/逐链路的 required/available/blocked_by）+ 控制台摘要

用法：
    python scripts/test-asset-map/build_capability_matrix.py \
        --capabilities docs/standards/project-adapters/futurewayu.capabilities.yaml \
        --pages docs/standards/project-adapters/out/futurewayu/page-inventory.json \
        --chains docs/standards/project-adapters/chains/futurewayu/manifest.json \
        --out docs/standards/project-adapters/out/futurewayu/capability-matrix.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capabilities", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--chains", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.capabilities).read_text(encoding="utf-8"))
    caps = {c["id"]: c for c in cfg.get("capabilities") or []}
    available = {cid for cid, c in caps.items() if c.get("available")}
    pages_doc = json.loads(Path(args.pages).read_text(encoding="utf-8"))
    pages = pages_doc.get("pages") if isinstance(pages_doc, dict) else pages_doc

    by_platform = (cfg.get("page_requirements") or {}).get("by_platform") or {}
    overrides = (cfg.get("page_requirements") or {}).get("overrides") or []

    def page_caps(pg: dict) -> list[str]:
        for ov in overrides:
            if ov.get("match") and ov["match"] in (pg.get("path") or ""):
                return list(ov.get("caps") or [])
        return list(by_platform.get(pg.get("platform"), []))

    page_rows = []
    for pg in pages:
        req = page_caps(pg)
        missing = [c for c in req if c not in available]
        page_rows.append({
            "page_id": pg.get("page_id"), "platform": pg.get("platform"), "name": pg.get("name"),
            "path": pg.get("path"), "required": req, "executable": not missing,
            "blocked_by": missing,
        })

    chain_rows = []
    chains_doc = None
    if args.chains and Path(args.chains).exists():
        chains_doc = json.loads(Path(args.chains).read_text(encoding="utf-8"))
        default_caps = (cfg.get("chain_requirements") or {}).get("default") or []
        kw_rules = (cfg.get("chain_requirements") or {}).get("by_domain_keyword") or []
        for ch in chains_doc.get("chains") or []:
            req = list(default_caps)
            for rule in kw_rules:
                kw = rule.get("keyword") or ""
                if kw and (kw in (ch.get("domain") or "") or kw in (ch.get("chain_id") or "")):
                    req += list(rule.get("caps") or [])
            req = sorted(set(req))
            missing = [c for c in req if c not in available]
            ready = ch.get("status") in ("ready", "ready-readonly")
            chain_rows.append({
                "chain_id": ch.get("chain_id"), "domain": ch.get("domain"),
                "priority": ch.get("priority"), "status": ch.get("status"),
                "required": req, "capability_ok": not missing,
                # 可执行 = 规格已就绪(ready) 且 能力齐备；骨架链不算可执行
                "executable": ready and not missing,
                "blocked_by": missing + ([] if ready else ["spec-skeleton"]),
            })

    def ratio(rows):
        return round(100 * sum(1 for r in rows if r["executable"]) / max(1, len(rows)), 1)

    blocked_by = Counter()
    for r in page_rows:
        for c in r["blocked_by"]:
            blocked_by[c] += 1
    chain_blocked = Counter()
    for r in chain_rows:
        for c in r["blocked_by"]:
            chain_blocked[c] += 1

    report = {
        "project": cfg.get("project"),
        "capabilities": [{"id": k, **v} for k, v in caps.items()],
        "available": sorted(available),
        "pages": {"total": len(page_rows), "executable": sum(1 for r in page_rows if r["executable"]),
                  "ratio": ratio(page_rows), "blocked_by": dict(blocked_by)},
        "chains": {"total": len(chain_rows), "executable": sum(1 for r in chain_rows if r["executable"]),
                   "ratio": ratio(chain_rows), "blocked_by": dict(chain_blocked)},
        "page_matrix": page_rows,
        "chain_matrix": chain_rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"pages: {report['pages']['executable']}/{report['pages']['total']} 可执行 "
          f"({report['pages']['ratio']}%)  阻塞原因={dict(blocked_by)}")
    if chain_rows:
        cap_ok = sum(1 for r in chain_rows if r.get("capability_ok"))
        print(f"chains: 能力齐备 {cap_ok}/{len(chain_rows)}，规格+能力可执行 "
              f"{report['chains']['executable']}/{len(chain_rows)} ({report['chains']['ratio']}%)  "
              f"阻塞原因={dict(chain_blocked)}")
    by_plat = defaultdict(lambda: [0, 0])
    for r in page_rows:
        by_plat[r["platform"]][1] += 1
        if r["executable"]:
            by_plat[r["platform"]][0] += 1
    for p, (ok, tot) in sorted(by_plat.items(), key=lambda kv: -kv[1][1]):
        print(f"  {p:8s} {ok}/{tot}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
