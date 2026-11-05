#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务域映射候选生成（把人工校准从"从零划"降为"确认候选"）。

思路：
1. 对接口路径做前缀聚类：/system/component/* → 候选域 system/component；
   通用前缀（system/client/device/account 等）自动下钻一级，避免一个大杂烩。
2. 组内少于 --min-size 的候选并入父级，避免碎片。
3. 若提供页面清单，用页面 path 的英文 token 与候选域做相似度提示（仅提示，不自动合并）。
4. 输出可直接粘贴的 adapter YAML 片段 + 覆盖率统计 + 与现有适配器的差异。

用法：
    python scripts/test-asset-map/suggest_domains.py \
        --endpoints docs/standards/project-adapters/sources/futurewayu.endpoints.json \
        --pages docs/standards/project-adapters/sources/futurewayu.pages.json \
        --existing docs/standards/project-adapters/futurewayu.adapter.yaml \
        --min-size 3 --out out/futurewayu/domain-suggest.yaml
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

# 需要下钻一级的“大杂烩”前缀（system/component、client/mall…）
GENERIC = {"system", "client", "device", "account", "resource", "camel", "api", "v1", "open"}
# 不再下钻、直接作为域的前缀（auth/login、alipay/notify 这类动词子路径应归并）
NO_DRILL = {"auth", "alipay", "wechat", "callback", "community", "advanced", "monitor",
            "youzan", "app", "admin", "api-service", "sports"}


def norm_prefix(path: str) -> str:
    segs = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    if not segs:
        return "/"
    first = segs[0]
    fl = first.lower()
    if fl in NO_DRILL:
        return "/" + first
    if fl in GENERIC and len(segs) > 1:
        return "/" + "/".join(segs[:2])
    return "/" + first


def load_endpoints(path: Path) -> list[dict]:
    if path.suffix in (".yaml", ".yml"):
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        eps = []
        for p, ops in (spec.get("paths") or {}).items():
            for m in (ops or {}):
                if m.lower() in {"get", "post", "put", "delete", "patch"}:
                    eps.append({"method": m.upper(), "path": p})
        return eps
    data = json.loads(path.read_text(encoding="utf-8"))
    return [{"method": d.get("method", "GET"), "path": d.get("path", "")} for d in data]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", required=True)
    ap.add_argument("--pages", default="")
    ap.add_argument("--existing", default="")
    ap.add_argument("--min-size", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    eps = load_endpoints(Path(args.endpoints))

    # 两级聚类：一级前缀 → 二级前缀（够大的独立成域，其余并入“一级-其他”）
    by_first: dict[str, list[str]] = defaultdict(list)
    for e in eps:
        segs = [s for s in e["path"].strip("/").split("/") if s and not s.startswith("{")]
        by_first[segs[0] if segs else "/"].append(e["path"])

    groups: dict[str, list[str]] = defaultdict(list)
    for first, paths in by_first.items():
        if first == "/":
            continue
        fl = first.lower()
        if fl in NO_DRILL or len(set(paths)) < args.min_size:
            groups["/" + first].extend(paths)
            continue
        sub: dict[str, list[str]] = defaultdict(list)
        for p in paths:
            segs = [s for s in p.strip("/").split("/") if s and not s.startswith("{")]
            sub[segs[1] if len(segs) > 1 else "__root__"].append(p)
        rest = []
        for seg2, ps in sub.items():
            if seg2 != "__root__" and len(set(ps)) >= args.min_size:
                groups["/" + first + "/" + seg2].extend(ps)
            else:
                rest.extend(ps)
        if rest:
            groups["/" + first].extend(rest)

    merged = groups

    # 页面 token 提示
    page_tokens: dict[str, set[str]] = defaultdict(set)
    if args.pages and Path(args.pages).exists():
        for pg in json.loads(Path(args.pages).read_text(encoding="utf-8")):
            for seg in re.split(r"[-/_]", pg.get("path", "")):
                if len(seg) >= 3 and seg.isascii():
                    page_tokens[seg.lower()].add(pg.get("name", ""))

    candidates = []
    for pref, paths in sorted(merged.items(), key=lambda kv: -len(set(kv[1]))):
        uniq = sorted(set(paths))
        name_parts = [p for p in pref.strip("/").split("/") if p]
        hint = sorted({t for part in name_parts for t in page_tokens if t in part.lower()})[:3]
        item = {
            "name": "域-" + "/".join(name_parts),
            "prefixes": [pref],
            "api_count": len(uniq),
            "page_hint": hint,
            "sample": uniq[:3],
        }
        # 兜底大域（未再细分）列出成员，便于人工决定是否继续拆
        if len(name_parts) == 1 and len(uniq) >= 30:
            hist = Counter()
            for u in uniq:
                segs = [x for x in u.strip("/").split("/") if x]
                hist["/" + "/".join(segs[:2]) if len(segs) > 1 else u] += 1
            item["catch_all"] = True
            item["members"] = [f"{k}({v})" for k, v in hist.most_common(12)]
        candidates.append(item)

    covered = sum(c["api_count"] for c in candidates)
    report = {
        "endpoints": len(eps),
        "unique_paths": len({e["path"] for e in eps}),
        "candidate_domains": len(candidates),
        "merged_small_groups": len([g for g in groups if len(set(groups[g])) < args.min_size]),
        "coverage_by_prefix": f"{covered}/{len(eps)}",
        "candidates": candidates,
    }

    # 与现有适配器对比
    if args.existing and Path(args.existing).exists():
        adapter = yaml.safe_load(Path(args.existing).read_text(encoding="utf-8"))
        existing = (adapter.get("interfaces") or {}).get("domain_map") or []
        gen_prefixes = {p for c in candidates for p in c["prefixes"]}
        ex_prefixes = {p for d in existing for p in (d.get("prefixes") or [])}
        report["vs_existing"] = {
            "existing_domains": len(existing),
            "same_prefix": len(gen_prefixes & ex_prefixes),
            "only_generated": sorted(gen_prefixes - ex_prefixes)[:15],
            "only_existing": sorted(ex_prefixes - gen_prefixes)[:15],
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    # 输出可粘贴的 YAML 片段
    yaml_lines = ["# 自动生成的业务域候选（人工确认后并入 adapter.interfaces.domain_map）", "domain_map:"]
    for c in candidates:
        yaml_lines.append(f"  - {{ name: {c['name']}, prefixes: [{', '.join(repr(p) for p in c['prefixes'])}] }}  # {c['api_count']} apis")
    out.with_suffix(".yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    print(f"endpoints={len(eps)} unique={report['unique_paths']} candidates={len(candidates)} "
          f"coverage={covered}/{len(eps)}")
    if "vs_existing" in report:
        v = report["vs_existing"]
        print(f"vs existing: domains {v['existing_domains']} -> {len(candidates)}, same_prefix={v['same_prefix']}")
        print(f"  only_generated={v['only_generated'][:8]}")
        print(f"  only_existing={v['only_existing'][:8]}")
    print("top candidates:")
    for c in candidates[:10]:
        print(f"  {c['name']:28s} {c['api_count']:3d} apis  hints={c['page_hint']}")
    print(f"-> {out} / {out.with_suffix('.yaml')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
