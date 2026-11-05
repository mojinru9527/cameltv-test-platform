#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""链路执行结果归因：把 FAIL 分成「产品缺陷 / 规格问题 / 能力缺失」，避免混为一谈。

分类规则（基于失败证据文本）：
- code=500            → product-500（缺参或内部异常被兜底，产品缺陷）
- code=401 且 /device → capability（需设备令牌）
- 其他 code 不符      → spec-or-product（需人工确认，默认列前）
- BLOCKED             → environment

用法：
    python scripts/test-asset-map/report_chains.py --summary runtime/chains/summary.csv \
        --out runtime/chains/chain-report.md
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def classify(failed_detail: str) -> list[dict]:
    out = []
    try:
        items = json.loads(failed_detail) if failed_detail.strip().startswith("[") else []
    except Exception:
        items = []
    for it in items:
        text = json.dumps(it, ensure_ascii=False)
        if "code=500" in text:
            kind = "product-500"
        elif "code=401" in text and "/device" in text:
            kind = "capability"
        elif "code=403" in text:
            kind = "authz-spec"
        elif "code=400" in text:
            kind = "param-required"
        else:
            kind = "spec-or-product"
        out.append({"kind": kind, "detail": it})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--readiness", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.summary, encoding="utf-8-sig")))
    kinds = Counter()
    grouped: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["result"] == "PASS":
            continue
        for f in classify(r.get("failed_detail", "")):
            kinds[f["kind"]] += 1
            grouped[f["kind"]].append({"chain": r["chain_id"], "path": (f["detail"].get("path") or f["detail"].get("step")),
                                       "fails": f["detail"].get("fails")})

    total_steps = sum(int(r["steps"]) for r in rows)
    passed_steps = sum(int(r["passed"]) for r in rows)
    chains_pass = sum(1 for r in rows if r["result"] == "PASS")

    lines = ["# 链路执行报告（只读批量）", "",
             f"- 链路：**{chains_pass}/{len(rows)} 通过**",
             f"- 步骤：**{passed_steps}/{total_steps} 通过（{round(100*passed_steps/max(1,total_steps),1)}%）**",
             f"- 失败归因：{dict(kinds)}", "",
             "## 按链路", "", "| 链路 | 优先级 | 结果 | 步骤 | 失败归因 |", "|---|---|---|---:|---|"]
    for r in rows:
        ks = Counter(x["kind"] for x in classify(r.get("failed_detail", "")))
        lines.append(f"| {r['chain_id']} | {r['priority']} | {r['result']} | {r['passed']}/{r['steps']} | "
                     f"{dict(ks) if ks else '-'} |")

    titles = {
        "product-500": "产品缺陷：缺参/内部异常返回 500 兜底",
        "capability": "能力缺失：设备接口需设备令牌（非缺陷）",
        "authz-spec": "规格口径：403 权限拒绝（需确认是否应允许）",
        "param-required": "规格口径：400 参数必填（设计如此，用例需补参）",
        "spec-or-product": "待确认",
    }
    for kind, items in grouped.items():
        lines += ["", f"## {titles.get(kind, kind)}（{len(items)}）", "",
                  "| 链路 | 接口 | 失败原因 |", "|---|---|---|"]
        for it in items:
            lines.append(f"| {it['chain']} | `{it['path']}` | {str(it['fails'])[:160]} |")

    lines += ["", "## 结论口径", "",
              "1. `product-500` 与 `param-required` 合并计入「缺参/内部异常 500」缺陷族，需按接口清单一次性整改。",
              "2. `capability` 不计缺陷，登记为环境能力缺口（设备令牌）。",
              "3. `spec-or-product` 必须人工复核后才可计入缺陷，避免把规格问题算成产品问题。"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"chains {chains_pass}/{len(rows)} | steps {passed_steps}/{total_steps} | kinds={dict(kinds)}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
