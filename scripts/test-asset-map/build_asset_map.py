#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试资产底图生成引擎（项目无关）。

输入：项目适配器 YAML（页面源 / 接口源 / 业务域映射 / 用例基线 / 准则库）
输出：page-inventory.json、rule-page-matrix.csv、interface-chain-graph.json、summary.json

用法：
    python scripts/test-asset-map/build_asset_map.py docs/standards/project-adapters/futurewayu.adapter.yaml
    python scripts/test-asset-map/build_asset_map.py docs/standards/project-adapters/cameltv-sports.adapter.yaml

设计原则：
1. 准则库（interaction-rules.json）跨项目恒定，不在本引擎内写死任何项目业务。
2. 项目差异只通过适配器声明（页面从哪来、接口从哪来、业务域怎么划）。
3. 引擎不访问数据库/网络；页面与接口必须由适配器指向已导出的抽取产物（抽取与生成分离）。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("需要 pyyaml: pip install pyyaml")

DEFAULT_RULES = (Path(__file__).resolve().parents[2] / ".claude" / "skills" /
                 "interaction-case-augmenter" / "references" / "interaction-rules.json")

KIND_KEYWORDS = {
    "list": ["list", "index", "search", "result", "board"],
    "form": ["edit", "add", "form", "config", "publish", "checksum", "checkout"],
    "detail": ["detail", "info", "view", "logistics", "profile"],
    "editor": ["dressup", "editor", "canvas", "design"],
    "monitor": ["monitor", "online", "cache", "log", "job"],
}
GENERIC_TOKENS = {"列表", "详情", "管理", "配置", "页面", "首页", "信息", "操作"}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(base: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def guess_kind(page: dict, kind_kw: dict) -> str:
    if page.get("page_kind"):
        return page["page_kind"]
    blob = (page.get("path", "") + " " + page.get("component", "") + " " + page.get("name", "")).lower()
    for kind, kws in kind_kw.items():
        if any(w.lower() in blob for w in kws):
            return kind
    return "list"


def load_pages(adapter: dict, base: Path) -> list[dict]:
    cfg = adapter.get("pages") or {}
    src = cfg.get("source", "file")
    kind_kw = dict(KIND_KEYWORDS)
    kind_kw.update(cfg.get("kind_keywords") or {})
    pages: list[dict] = []

    if src == "file":
        path = resolve(base, cfg["path"])
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data["pages"] if isinstance(data, dict) and "pages" in data else data
        for i, p in enumerate(raw):
            pages.append({
                "platform": p.get("platform") or cfg.get("default_platform", "unknown"),
                "page_id": p.get("page_id") or f"PG-{i+1:03d}",
                "group": p.get("group", ""),
                "name": p.get("name") or p.get("path", ""),
                "path": p.get("path", ""),
                "component": p.get("component", ""),
                "page_kind": guess_kind(p, kind_kw),
            })
    elif src == "openapi_tags":
        path = resolve(base, cfg["path"])
        spec = load_yaml(path)
        for i, tag in enumerate(spec.get("tags") or []):
            name = tag.get("name") if isinstance(tag, dict) else str(tag)
            pages.append({"platform": cfg.get("default_platform", "api"),
                          "page_id": f"TAG-{i+1:02d}", "group": "接口域",
                          "name": name, "path": f"/tag/{name}", "component": "",
                          "page_kind": "list"})
    elif src == "static":
        for i, p in enumerate(cfg.get("items") or []):
            pages.append({"platform": p.get("platform", "unknown"), "page_id": p.get("page_id", f"PG-{i+1:03d}"),
                          "group": p.get("group", ""), "name": p.get("name", ""), "path": p.get("path", ""),
                          "component": "", "page_kind": guess_kind(p, kind_kw)})
    else:
        raise SystemExit(f"未知 pages.source: {src}")
    return pages


def load_interfaces(adapter: dict, base: Path) -> list[dict]:
    cfg = adapter.get("interfaces") or {}
    src = cfg.get("source", "endpoints_json")
    path = resolve(base, cfg["path"])
    eps: list[dict] = []
    if src == "endpoints_json":
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data:
            eps.append({"method": e.get("method", "GET"), "path": e.get("path", ""),
                        "name": e.get("name", ""), "folder": e.get("folder", "")})
    elif src == "openapi":
        spec = load_yaml(path)
        for p, ops in (spec.get("paths") or {}).items():
            for method, op in (ops or {}).items():
                if method.lower() not in {"get", "post", "put", "delete", "patch", "head", "options"}:
                    continue
                eps.append({"method": method.upper(), "path": p,
                            "name": (op or {}).get("summary", ""),
                            "folder": ",".join((op or {}).get("tags") or [])})
    else:
        raise SystemExit(f"未知 interfaces.source: {src}")
    return eps


def classify(eps: list[dict], cfg: dict) -> list[dict]:
    domain_map = cfg.get("domain_map") or []
    default = cfg.get("default_domain", "其他")
    stage_kw = cfg.get("stage_keywords") or {}
    stages = stage_kw or {
        "create": ["新增", "创建", "add", "create", "upload", "上传", "register", "登录"],
        "process": ["处理", "生成", "精修", "refine", "sync", "同步", "ai"],
        "review": ["审核", "review", "质检", "audit"],
        "publish": ["上架", "publish", "发布", "启用", "bind", "绑定"],
        "list": ["列表", "list", "分页", "page", "search", "查询列表"],
        "detail": ["详情", "detail", "info", "查询", "get"],
        "transact": ["结算", "checkout", "下单", "提交", "submit", "支付", "pay", "退款", "refund", "取消", "cancel", "核销"],
        "update": ["修改", "更新", "update", "edit", "解绑"],
        "delete": ["删除", "delete", "remove", "下架"],
    }
    order = ["create", "process", "review", "publish", "list", "detail", "transact", "update", "delete", "other"]

    def domain_of(p: str) -> str:
        for d in domain_map:
            for pref in d.get("prefixes", []):
                if p.startswith(pref):
                    return d["name"]
        return default

    def stage_of(e: dict) -> str:
        t = f'{e.get("name", "")} {e.get("path", "")}'.lower()
        for s, kws in stages.items():
            if any(str(k).lower() in t for k in kws):
                return s
        return "other"

    out = []
    for e in eps:
        out.append({**e, "domain": domain_of(e.get("path", "")), "stage": stage_of(e)})
    return out, order, domain_of


def build_graph(classified: list[dict], order: list[str]) -> dict:
    by_domain = defaultdict(list)
    for e in classified:
        by_domain[e["domain"]].append(e)
    chains = {}
    for d, items in by_domain.items():
        stages = sorted({i["stage"] for i in items}, key=lambda s: order.index(s) if s in order else 99)
        nodes = [{"stage": s, "apis": [f'{i["method"]} {i["path"]}' for i in items if i["stage"] == s]}
                 for s in stages]
        chains[d] = {"domain": d, "api_count": len(items), "stages": stages, "nodes": nodes}
    return chains


def load_cases(adapter: dict, base: Path):
    cfg = adapter.get("cases") or {}
    if not cfg.get("path"):
        return []
    path = resolve(base, cfg["path"])
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        fun = data.get("functional") or data.get("cases") or []
        deep = data.get("deep") or []
        return fun + deep
    return data


def build_matrix(pages: list[dict], rules: list[dict], cases: list[dict]) -> list[dict]:
    rows = []
    heads, expects = [], []
    for c in cases:
        cid = c.get("用例编号") or c.get("id")
        head = " ".join(str(c.get(k, "")) for k in ("用例标题", "模块", "深度类别", "需求名称", "title", "module"))
        expects_ = str(c.get("预期结果", "")) + " " + str(c.get("expected", ""))
        heads.append((cid, head))
        expects.append((cid, expects_))

    for pg in pages:
        kind = pg["page_kind"]
        tokens = [t for t in re.split(r"[-/（()）\s]", pg["name"]) if len(t) >= 2 and t not in GENERIC_TOKENS][:3]
        for r in rules:
            kinds = r.get("page_kinds") or ["all"]
            if not ("all" in kinds or kind in kinds):
                rows.append({"page_id": pg["page_id"], "platform": pg["platform"], "page": pg["name"],
                             "page_kind": kind, "rule_id": r["rule_id"], "rule": r["category"],
                             "invariant": r["invariant"], "state": "N/A", "evidence_case": ""})
                continue
            state, ev = "NONE", ""
            if tokens and cases:
                kws = r.get("keywords") or [r["category"]]
                for cid, exp in expects:
                    if not any(k in exp for k in kws):
                        continue
                    for cid2, head in heads:
                        if cid2 == cid and any(t in head for t in tokens):
                            state, ev = "COVERED", cid
                            break
                    if state == "COVERED":
                        break
            rows.append({"page_id": pg["page_id"], "platform": pg["platform"], "page": pg["name"],
                         "page_kind": kind, "rule_id": r["rule_id"], "rule": r["category"],
                         "invariant": r["invariant"], "state": state, "evidence_case": ev})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("adapter")
    ap.add_argument("--rules", default=None)
    args = ap.parse_args()

    adapter_path = Path(args.adapter).resolve()
    adapter = load_yaml(adapter_path)
    base = adapter_path.parent
    rules_path = Path(args.rules).resolve() if args.rules else DEFAULT_RULES
    rules = json.loads(rules_path.read_text(encoding="utf-8"))["rules"]

    pages = load_pages(adapter, base)
    eps = load_interfaces(adapter, base)
    classified, order, _ = classify(eps, adapter.get("interfaces") or {})
    chains = build_graph(classified, order)
    cases = load_cases(adapter, base)
    rows = build_matrix(pages, rules, cases)

    out = Path(adapter.get("output_dir") or (base / "out"))
    if not out.is_absolute():
        out = (base / out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    (out / "page-inventory.json").write_text(
        json.dumps({"project": adapter.get("project"), "display_name": adapter.get("display_name"),
                    "pages": pages, "rules": rules}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "interface-chain-graph.json").write_text(
        json.dumps({"project": adapter.get("project"), "total_endpoints": len(eps),
                    "unique_paths": len({e["path"] for e in eps}),
                    "domains": len(chains), "chains": chains}, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "rule-page-matrix.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    applicable = [r for r in rows if r["state"] != "N/A"]
    covered = [r for r in applicable if r["state"] == "COVERED"]
    page_stat = defaultdict(lambda: [0, 0])
    for r in applicable:
        page_stat[(r["platform"], r["page"])][1] += 1
        if r["state"] == "COVERED":
            page_stat[(r["platform"], r["page"])][0] += 1
    zero_pages = [f"{p}/{pg}" for (p, pg), (c, t) in page_stat.items() if c == 0]
    rule_stat = defaultdict(lambda: [0, 0])
    for r in applicable:
        rule_stat[r["rule_id"]][1] += 1
        if r["state"] == "COVERED":
            rule_stat[r["rule_id"]][0] += 1

    summary = {
        "project": adapter.get("project"),
        "pages": len(pages),
        "pages_by_platform": dict(Counter(p["platform"] for p in pages)),
        "rules": len(rules),
        "matrix_cells": len(rows),
        "applicable_cells": len(applicable),
        "covered_cells": len(covered),
        "coverage_pct": round(100 * len(covered) / max(1, len(applicable)), 1),
        "zero_coverage_pages": len(zero_pages),
        "zero_coverage_page_list": zero_pages,
        "worst_rules": sorted(
            [{"rule_id": k, "applicable": v[1], "covered": v[0],
              "pct": round(100 * v[0] / max(1, v[1]), 1)} for k, v in rule_stat.items()],
            key=lambda x: x["pct"])[:8],
        "endpoints": len(eps),
        "unique_paths": len({e["path"] for e in eps}),
        "domains": len(chains),
        "unassigned_endpoints": [f'{e["method"]} {e["path"]}' for e in classified if e["domain"] == "其他"],
        "chains": sorted([{"domain": c["domain"], "api_count": c["api_count"], "stages": c["stages"]}
                          for c in chains.values()], key=lambda x: -x["api_count"]),
        "cases_loaded": len(cases),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"project={summary['project']} pages={summary['pages']} rules={summary['rules']} "
          f"cells={summary['matrix_cells']} applicable={summary['applicable_cells']} "
          f"covered={summary['covered_cells']} ({summary['coverage_pct']}%)")
    print(f"endpoints={summary['endpoints']} unique_paths={summary['unique_paths']} domains={summary['domains']} "
          f"unassigned={len(summary['unassigned_endpoints'])}")
    print(f"zero_coverage_pages={summary['zero_coverage_pages']}")
    print(f"worst_rules={[ (w['rule_id'], w['pct']) for w in summary['worst_rules'][:5] ]}")
    print(f"output -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
