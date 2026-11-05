#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面源适配器集合（把"可访问环境 / 源码 / 小程序包 / PRD"统一成 pages 清单）。

子命令：
    crawl-web    用 Playwright 爬已登录/公开的 Web 后台，产出页面清单
    scan-source  扫描前端源码路由（Vue Router / React Router / Next.js / views 目录）
    scan-mp      解析小程序 app.json + 页面 json 标题
    parse-prd    从 PRD/需求文本里抽取"页面/模块"候选
    merge        合并多来源，标注来源与缺口（PRD 有、实现无 / 实现有、PRD 无）

统一输出：JSON 数组，元素字段 platform/page_id/group/name/path/page_kind/source/evidence
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KIND_RULES = [
    ("form", ["edit", "add", "create", "form", "config", "publish", "checkout", "publish"]),
    ("detail", ["detail", "info", "view", "profile", "logistics", "workbench"]),
    ("editor", ["dressup", "editor", "canvas", "design"]),
    ("monitor", ["monitor", "online", "cache", "log", "job", "gen"]),
    ("list", ["list", "index", "search", "result", "board"]),
]


def infer_kind(text: str) -> str:
    t = (text or "").lower()
    for kind, kws in KIND_RULES:
        if any(k in t for k in kws):
            return kind
    return "list"


def norm_path(p: str) -> str:
    p = "/" + (p or "").strip().strip("/")
    p = re.sub(r"/+", "/", p)
    return p


def emit(pages: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"pages={len(pages)} -> {out}")


# --------------------------------------------------------------------- crawl-web
def crawl_web(args) -> int:
    from playwright.sync_api import sync_playwright

    state = json.loads(Path(args.state).read_text(encoding="utf-8")) if args.state else None
    pages: list[dict] = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=not args.headed)
        ctx = b.new_context(viewport={"width": 1600, "height": 950}, locale="zh-CN")
        if state:
            if state.get("cookies"):
                ctx.add_cookies(state["cookies"])
            ls = state.get("localStorage") or {}
            if ls:
                ctx.add_init_script(
                    "(()=>{const o=%s;for(const k in o){try{localStorage.setItem(k,o[k])}catch(e){}}})()"
                    % json.dumps(ls, ensure_ascii=False))
        page = ctx.new_page()
        page.goto(args.base_url.rstrip("/") + (args.entry or "/"), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(args.wait_ms)

        links = page.evaluate("""() => {
          const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const out = [];
          for (const a of document.querySelectorAll('a[href]')) {
            if (!vis(a)) continue;
            const href = a.getAttribute('href') || '';
            if (!href.startsWith('/') || href.startsWith('//')) continue;
            const text = (a.innerText || '').trim().replace(/\\s+/g, ' ');
            if (!text || text.length > 40) continue;
            out.push({path: href.split('?')[0], name: text});
          }
          return out;
        }""")
        seen = set()
        for l in links:
            pth = norm_path(l["path"])
            if pth in seen:
                continue
            seen.add(pth)
            pages.append({"platform": args.platform, "page_id": f"{args.prefix}-{len(pages)+1:03d}",
                          "group": args.group, "name": l["name"], "path": pth,
                          "component": "", "page_kind": infer_kind(pth + " " + l["name"]),
                          "source": "crawl-web", "evidence": "a[href] on " + args.entry})
        if args.visit:
            for pg in pages[: args.max_pages]:
                try:
                    page.goto(args.base_url.rstrip("/") + pg["path"], wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(1200)
                    title = page.evaluate("() => document.title")
                    pg["page_title"] = title
                    pg["reachable"] = True
                except Exception as e:
                    pg["reachable"] = False
                    pg["error"] = str(e)[:120]
        b.close()
    emit(pages, Path(args.out))
    return 0


# --------------------------------------------------------------------- scan-source
def scan_source(args) -> int:
    root = Path(args.root)
    pages: list[dict] = []
    files = list(root.rglob("*"))
    if args.framework in ("auto", "vue"):
        for f in files:
            if f.suffix not in (".ts", ".js") or "router" not in str(f).lower():
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            # path: '/x'  ...  meta: { title: 'y' }
            for m in re.finditer(r"path:\s*['\"]([^'\"]+)['\"](.{0,400}?)", text, re.S):
                pth, tail = m.group(1), m.group(2)
                if pth.startswith(":"):
                    continue
                tm = re.search(r"title:\s*['\"]([^'\"]+)['\"]", tail)
                comp = re.search(r"import\(['\"]@/([^'\"]+\.vue)['\"]\)", tail)
                pages.append({"platform": args.platform, "page_id": f"SRC-{len(pages)+1:03d}",
                              "group": args.group, "name": tm.group(1) if tm else pth,
                              "path": norm_path(pth),
                              "component": comp.group(1) if comp else "",
                              "page_kind": infer_kind(pth + " " + (tm.group(1) if tm else "")),
                              "source": "scan-source", "evidence": str(f.relative_to(root)).replace("\\", "/")})
        if args.also_views:
            views = root / args.views_dir
            if views.exists():
                for v in views.rglob("*.vue"):
                    rel = v.relative_to(views).as_posix()
                    if rel.startswith("components/") or "/components/" in rel:
                        continue
                    pages.append({"platform": args.platform, "page_id": f"VIEW-{len(pages)+1:03d}",
                                  "group": args.group, "name": v.stem, "path": "/__view__/" + rel,
                                  "component": rel, "page_kind": infer_kind(rel),
                                  "source": "scan-source-views", "evidence": f"views/{rel}"})
    elif args.framework == "react":
        for f in files:
            if f.suffix not in (".tsx", ".jsx", ".ts", ".js"):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"<Route[^>]*path=['\"]([^'\"]+)['\"]", text):
                pth = m.group(1)
                pages.append({"platform": args.platform, "page_id": f"SRC-{len(pages)+1:03d}",
                              "group": args.group, "name": pth, "path": norm_path(pth), "component": "",
                              "page_kind": infer_kind(pth), "source": "scan-source",
                              "evidence": str(f.relative_to(root)).replace("\\", "/")})
    elif args.framework == "next":
        for f in files:
            if f.name not in ("page.tsx", "page.jsx", "page.js", "page.ts"):
                continue
            rel = f.parent.relative_to(root).as_posix()
            pth = "/" + re.sub(r"\(.*?\)/?", "", rel).strip("/")
            pages.append({"platform": args.platform, "page_id": f"SRC-{len(pages)+1:03d}",
                          "group": args.group, "name": pth, "path": norm_path(pth), "component": "",
                          "page_kind": infer_kind(pth), "source": "scan-source",
                          "evidence": rel})
    # 去重（同 path 保留首个）
    dedup, seen = [], set()
    for pg in pages:
        if pg["path"] in seen:
            continue
        seen.add(pg["path"])
        dedup.append(pg)
    emit(dedup, Path(args.out))
    return 0


# --------------------------------------------------------------------- scan-mp
def scan_mp(args) -> int:
    app = json.loads(Path(args.app_json).read_text(encoding="utf-8"))
    root = Path(args.app_json).parent
    entries: list[tuple[str, str]] = []
    for pth in app.get("pages") or []:
        entries.append((pth, "主包"))
    for sub in app.get("subPackages") or app.get("subpackages") or []:
        prefix = (sub.get("root") or "").rstrip("/")
        for item in sub.get("pages") or []:
            entries.append((f"{prefix}/{item}", prefix))
    pages = []
    for i, (pth, group) in enumerate(entries):
        title = ""
        for cand in (root / f"{pth}.json", root / "pages" / f"{pth}.json"):
            if cand.exists():
                try:
                    title = json.loads(cand.read_text(encoding="utf-8")).get("navigationBarTitleText", "") or ""
                except Exception:
                    pass
                break
        name = title or pth.split("/")[-1]
        pages.append({"platform": args.platform, "page_id": f"MP-{i+1:03d}", "group": group,
                      "name": name, "path": "/" + pth, "component": pth,
                      "page_kind": infer_kind(pth + " " + name), "source": "scan-mp",
                      "evidence": str(Path(args.app_json).name)})
    emit(pages, Path(args.out))
    return 0


# --------------------------------------------------------------------- parse-prd
PAGE_HINT = re.compile(r"(页面|页|模块|入口|弹窗|抽屉|列表|详情|表单|工作台|大屏|屏)")
SKIP = re.compile(r"(接口|字段|数据库|表结构|SQL|字段名|参数|返回值|同步|校验|失败|成功|状态码)")
SENTENCE = re.compile(r"[。；，、！？:：]")


def parse_prd(args) -> int:
    text = Path(args.input).read_text(encoding="utf-8", errors="ignore")
    cands: list[dict] = []
    seen = set()
    for raw in text.splitlines():
        s = re.sub(r"^#+\s*", "", raw.strip())
        s = re.sub(r"^[\d\.\-、（）()\s]+", "", s).strip()
        # 只保留“像页面标题”的短行：<=16 字、不含句读、不是接口/字段/页脚
        if not (2 <= len(s) <= 16):
            continue
        if SENTENCE.search(s) or SKIP.search(s) or PAGE_HINT.search(s) is None:
            continue
        if re.match(r"^(第\s*\d+\s*页|共\s*\d+\s*页|页\s|图\s|表\s|回\s|注\s)", s):
            continue
        if re.search(r"共\s*\d+\s*页", s):
            continue
        key = re.sub(r"\s+", "", s)[:12]
        if not key or key in seen:
            continue
        seen.add(key)
        cands.append({"platform": args.platform, "page_id": f"PRD-{len(cands)+1:03d}", "group": "PRD",
                      "name": s, "path": "", "component": "", "page_kind": infer_kind(s),
                      "source": "parse-prd", "evidence": Path(args.input).name})
        if len(cands) >= args.limit:
            break
    emit(cands, Path(args.out))
    return 0


# --------------------------------------------------------------------- merge
def merge(args) -> int:
    sources = {}
    for spec in args.source:
        label, path = spec.split("=", 1)
        sources[label] = json.loads(Path(path).read_text(encoding="utf-8"))

    merged: list[dict] = []
    index: dict[str, dict] = {}

    def key_of(pg: dict) -> str:
        if pg.get("path") and not pg["path"].startswith("/__view__"):
            return "path:" + norm_path(pg["path"]).lower()
        return "name:" + re.sub(r"\s+", "", pg.get("name", "")).lower()

    # 先合并“有路径”的实现来源，再处理 PRD（PRD 无路径，按名称弱匹配归并）
    ordered = sorted(sources.items(), key=lambda kv: (kv[0] == "prd", kv[0]))
    for label, pages in ordered:
        for pg in pages:
            k = key_of(pg)
            if k in index:
                tgt = index[k]
                tgt["sources"] = sorted(set(tgt.get("sources", []) + [label]))
                if not tgt.get("component") and pg.get("component"):
                    tgt["component"] = pg["component"]
                if tgt.get("name") in ("", None) and pg.get("name"):
                    tgt["name"] = pg["name"]
                continue
            if pg.get("source") == "parse-prd" or label == "prd":
                nm = re.sub(r"\s+", "", pg.get("name", ""))
                hit = None
                for item in merged:
                    inm = re.sub(r"\s+", "", item.get("name", ""))
                    if not nm or not inm:
                        continue
                    if nm == inm or (len(nm) >= 3 and (nm in inm or inm in nm)):
                        hit = item
                        break
                if hit is not None:
                    hit["sources"] = sorted(set(hit.get("sources", []) + [label]))
                    continue
            item = {**pg, "sources": [label]}
            index[k] = item
            merged.append(item)

    # PRD-only 候选：按名称包含关系做弱匹配
    prd = [m for m in merged if m["sources"] == ["prd"]]
    impl = [m for m in merged if m["sources"] != ["prd"]]
    gaps = []
    for c in prd:
        name = re.sub(r"\s+", "", c["name"])
        hit = next((i for i in impl if name[:6] and name[:6] in re.sub(r"\s+", "", i["name"])), None)
        if not hit:
            gaps.append({"kind": "PRD_ONLY", "name": c["name"], "page_id": c["page_id"],
                         "reason": "需求中出现、实现来源未找到对应页面"})
    for i in impl:
        if i["sources"] and "prd" not in i["sources"]:
            pass  # 实现有、PRD 无：由报告侧统计，不逐条生成缺口

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    gap_path = out.with_name(out.stem + ".gaps.json")
    gap_path.write_text(json.dumps(gaps, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"merged={len(merged)} prd_only_gaps={len(gaps)} -> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("crawl-web"); c.set_defaults(fn=crawl_web)
    c.add_argument("--base-url", required=True); c.add_argument("--state", default="")
    c.add_argument("--entry", default="/"); c.add_argument("--wait-ms", type=int, default=5000)
    c.add_argument("--platform", default="web"); c.add_argument("--group", default="")
    c.add_argument("--prefix", default="WEB"); c.add_argument("--out", required=True)
    c.add_argument("--visit", action="store_true"); c.add_argument("--max-pages", type=int, default=60)
    c.add_argument("--headed", action="store_true")

    s = sub.add_parser("scan-source"); s.set_defaults(fn=scan_source)
    s.add_argument("--root", required=True); s.add_argument("--framework", default="auto")
    s.add_argument("--platform", default="web"); s.add_argument("--group", default="")
    s.add_argument("--also-views", action="store_true"); s.add_argument("--views-dir", default="views")
    s.add_argument("--out", required=True)

    m = sub.add_parser("scan-mp"); m.set_defaults(fn=scan_mp)
    m.add_argument("--app-json", required=True); m.add_argument("--platform", default="mini_program")
    m.add_argument("--out", required=True)

    p = sub.add_parser("parse-prd"); p.set_defaults(fn=parse_prd)
    p.add_argument("--input", required=True); p.add_argument("--platform", default="prd")
    p.add_argument("--limit", type=int, default=150)
    p.add_argument("--out", required=True)

    g = sub.add_parser("merge"); g.set_defaults(fn=merge)
    g.add_argument("--source", action="append", required=True, help="label=path")
    g.add_argument("--out", required=True)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
