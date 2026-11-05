#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互准则断言执行器（把 A01–A24 从"文本口径"变成"可执行断言"）。

用法：
    # Web 断言：对页面清单逐页测量 R07 溢出 / R21 对比度 / R22 响应式 / R23 键盘焦点
    python scripts/test-asset-map/run_assertions.py web \
        --pages pages.json --state state.json --base-url https://example.com \
        --rules R07,R21,R22,R23 --limit 10 --out web-assertions.csv

    # HTTP 断言：按声明式 spec 校验 R11 权限 / R12 越权 / R05 幂等 / R06 参数 / R19 一致性
    python scripts/test-asset-map/run_assertions.py http \
        --spec http-checks.json --env env.json --out http-assertions.csv

输出 CSV 列：rule_id,page,assertion,status,metric,evidence
status: PASS / FAIL / BLOCKED / N/A
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path


# ------------------------------------------------------------------ Web assertions
JS_METRICS = r"""() => {
  const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const res = {};
  // A07 溢出：容器 scrollWidth 超过 clientWidth
  let overflow = 0, samples = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    if (!(el.innerText||'').trim()) continue;  // 只看有文本的容器，排除图片/装饰盒
    const cs = getComputedStyle(el);
    if (['hidden','auto','scroll'].includes(cs.overflowX) || cs.overflow === 'hidden') continue;
    if (cs.textOverflow === 'ellipsis' || cs.whiteSpace === 'nowrap') continue;
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) {
      overflow++;
      if (samples.length < 3) samples.push((el.className||el.tagName).toString().slice(0,50) + ':' + el.scrollWidth + '/' + el.clientWidth);
    }
  }
  res.overflowCount = overflow; res.overflowSamples = samples;

  // A21 对比度
  function lum(c){const[r,g,b]=c.map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*r+0.7152*g+0.0722*b;}
  function parse(s){const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const q=m[1].split(',').map(Number);return {rgb:[q[0],q[1],q[2]],a:q.length>3?q[3]:1};}
  function bgOf(el){let e=el;while(e){const q=parse(getComputedStyle(e).backgroundColor);if(q&&q.a>0.1)return q.rgb;e=e.parentElement;}return[255,255,255];}
  let worst = null, lowCount = 0;
  for (const el of [...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && (e.innerText||'').trim().length>=2)) {
    if (!vis(el)) continue;
    const cs = getComputedStyle(el);
    const fg = parse(cs.color); if (!fg) continue;
    const bg = bgOf(el); const l1=lum(fg.rgb), l2=lum(bg);
    const ratio = (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
    const fs = parseFloat(cs.fontSize)||12, bold = parseInt(cs.fontWeight)>=700;
    const need = (fs>=24 || (fs>=18.66 && bold)) ? 3.0 : 4.5;
    if (!worst || ratio < worst.ratio) worst = {ratio:Math.round(ratio*100)/100, need, text:(el.innerText||'').trim().slice(0,20), size:fs};
    if (ratio < need) lowCount++;
  }
  res.contrastWorst = worst; res.contrastLow = lowCount;
  res.docScrollWidth = document.documentElement.scrollWidth;
  res.innerWidth = window.innerWidth;
  return res;
}"""

JS_FOCUS = r"""() => {
  const out = [];
  for (let i = 0; i < 8; i++) {
    const el = document.activeElement;
    out.push({tag: el ? el.tagName : null, text: el ? (el.innerText||el.getAttribute('placeholder')||'').slice(0,20) : '',
              visible: el ? !!(el.offsetWidth||el.offsetHeight) : false});
    // 主动 tab 由外部驱动
  }
  return out;
}"""


def web_assertions(args) -> int:
    from playwright.sync_api import sync_playwright

    pages = json.loads(Path(args.pages).read_text(encoding="utf-8"))
    pages = [p for p in pages if p.get("path") and not p["path"].startswith("/__view__")]
    if pages and pages[0].get("platform"):
        pass
    rules = [r.strip().upper() for r in args.rules.split(",") if r.strip()]
    state = json.loads(Path(args.state).read_text(encoding="utf-8")) if args.state else None
    rows = []
    t0 = time.time()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        if state:
            if state.get("cookies"):
                ctx.add_cookies(state["cookies"])
            if state.get("localStorage"):
                ctx.add_init_script(
                    "(()=>{const o=%s;for(const k in o){try{localStorage.setItem(k,o[k])}catch(e){}}})()"
                    % json.dumps(state["localStorage"], ensure_ascii=False))
        page = ctx.new_page()
        page.set_default_timeout(args.timeout)

        for pg in pages[: args.limit]:
            url = args.base_url.rstrip("/") + pg["path"]
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
                page.wait_for_timeout(args.wait_ms)
            except Exception as e:
                for r in rules:
                    rows.append({"rule_id": r, "page": pg.get("name", pg["path"]), "assertion": "",
                                 "status": "BLOCKED", "metric": "", "evidence": str(e)[:160]})
                continue
            m = page.evaluate(JS_METRICS)
            for r in rules:
                if r == "R07":
                    ok = m["overflowCount"] == 0
                    rows.append({"rule_id": r, "page": pg.get("name", pg["path"]), "assertion": "A07",
                                 "status": "PASS" if ok else "FAIL",
                                 "metric": f"overflow={m['overflowCount']}",
                                 "evidence": ";".join(m["overflowSamples"])})
                elif r == "R21":
                    w = m["contrastWorst"]
                    ok = bool(w) and w["ratio"] >= w["need"]
                    rows.append({"rule_id": r, "page": pg.get("name", pg["path"]), "assertion": "A21",
                                 "status": "PASS" if ok else "FAIL",
                                 "metric": f"worst={w['ratio'] if w else None} low={m['contrastLow']}",
                                 "evidence": json.dumps(w, ensure_ascii=False) if w else ""})
                elif r == "R22":
                    sweep = []
                    try:
                        for w, h in ((1280, 800), (1440, 900), (1920, 1080)):
                            page.set_viewport_size({"width": w, "height": h})
                            page.wait_for_timeout(350)
                            mm = page.evaluate("() => ({s: document.documentElement.scrollWidth, v: window.innerWidth})")
                            sweep.append((w, mm["s"], mm["v"], mm["s"] <= mm["v"] + 1))
                    except Exception as e:
                        sweep = [("ERR", 0, 0, False)]
                    page.set_viewport_size({"width": 1440, "height": 900})
                    bad = [x for x in sweep if not x[3]]
                    rows.append({"rule_id": r, "page": pg.get("name", pg["path"]), "assertion": "A22",
                                 "status": "PASS" if not bad else "FAIL",
                                 "metric": " ".join(f"{w}:{s}/{v}" for w, s, v, _ in sweep),
                                 "evidence": f"溢出视口={[x[0] for x in bad]}"})
                elif r == "R23":
                    seq = []
                    try:
                        for _ in range(8):
                            page.keyboard.press("Tab")
                            page.wait_for_timeout(80)
                            seq.append(page.evaluate("() => { const e=document.activeElement; return e? (e.tagName+'|'+(e.innerText||e.getAttribute('placeholder')||'').slice(0,16)+'|'+(!!(e.offsetWidth||e.offsetHeight))) : 'null'; }"))
                    except Exception as e:
                        seq = [f"ERR {e}"]
                    lost = [s for s in seq if s.startswith("BODY|") or s == "null"]
                    rows.append({"rule_id": r, "page": pg.get("name", pg["path"]), "assertion": "A23",
                                 "status": "FAIL" if lost else "PASS",
                                 "metric": f"tab_steps={len(seq)} lost={len(lost)}",
                                 "evidence": " > ".join(seq[:5])})
        b.close()
    write_csv(rows, args.out)
    print(f"web assertions: pages={min(len(pages), args.limit)} rules={rules} rows={len(rows)} {int(time.time()-t0)}s -> {args.out}")
    return 0


# ------------------------------------------------------------------ HTTP assertions
def http_assertions(args) -> int:
    import requests
    import urllib3
    urllib3.disable_warnings()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    env = json.loads(Path(args.env).read_text(encoding="utf-8"))
    base = env["base_url"].rstrip("/")
    rows = []
    for chk in spec:
        rule = chk.get("rule", "")
        headers = dict(chk.get("headers") or {})
        auth = chk.get("auth")
        if auth == "admin":
            headers["Authorization"] = "Bearer " + env["admin_token"]
            headers["clientid"] = env.get("clientid", "")
        elif auth == "client":
            headers["token"] = env["client_token"]
        method = chk.get("method", "GET").upper()
        path = chk["path"]
        body = chk.get("body")
        try:
            t0 = time.time()
            r = requests.request(method, base + path, headers=headers,
                                 json=body if isinstance(body, (dict, list)) else None,
                                 data=body if isinstance(body, str) else None,
                                 timeout=chk.get("timeout", 60), verify=False)
            dt = int((time.time() - t0) * 1000)
            try:
                j = r.json()
            except Exception:
                j = {"_raw": r.text[:200]}
        except Exception as e:
            rows.append({"rule_id": rule, "page": chk.get("id", path), "assertion": chk.get("assertion", ""),
                         "status": "BLOCKED", "metric": "", "evidence": str(e)[:160]})
            continue
        expect = chk.get("expect") or {}
        fails = []
        if "http" in expect and r.status_code != expect["http"]:
            fails.append(f"http={r.status_code}!= {expect['http']}")
        if "code" in expect and j.get("code") != expect["code"]:
            fails.append(f"code={j.get('code')}!={expect['code']}")
        if "code_in" in expect and j.get("code") not in expect["code_in"]:
            fails.append(f"code={j.get('code')}!in {expect['code_in']}")
        present = chk.get("present", expect.get("present"))
        if present and not isinstance(j.get("data"), (dict, list)):
            fails.append("data absent")
        absent = chk.get("absent_fields") or expect.get("absent_fields") or []
        if absent:
            blob = json.dumps(j, ensure_ascii=False)
            for f in absent:
                if f in blob:
                    fails.append(f"leaked:{f}")
        max_ms = chk.get("max_ms", expect.get("max_ms"))
        if max_ms is not None and dt > max_ms:
            fails.append(f"{dt}ms>{max_ms}ms")
        rows.append({"rule_id": rule, "page": chk.get("id", path), "assertion": chk.get("assertion", ""),
                     "status": "PASS" if not fails else "FAIL",
                     "metric": f"http={r.status_code} code={j.get('code')} {dt}ms",
                     "evidence": ";".join(fails)[:300]})
    write_csv(rows, args.out)
    print(f"http assertions: checks={len(spec)} rows={len(rows)} -> {args.out}")
    return 0


def write_csv(rows: list[dict], out: str) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rule_id", "page", "assertion", "status", "metric", "evidence"])
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("web"); w.set_defaults(fn=web_assertions)
    w.add_argument("--pages", required=True); w.add_argument("--state", default="")
    w.add_argument("--base-url", required=True); w.add_argument("--rules", default="R07,R21,R22,R23")
    w.add_argument("--limit", type=int, default=10); w.add_argument("--out", required=True)
    w.add_argument("--timeout", type=int, default=45000); w.add_argument("--wait-ms", type=int, default=4000)

    h = sub.add_parser("http"); h.set_defaults(fn=http_assertions)
    h.add_argument("--spec", required=True); h.add_argument("--env", required=True)
    h.add_argument("--out", required=True)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
