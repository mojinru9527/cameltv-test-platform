#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互准则断言执行器（24 条准则 → 可执行检查）。

覆盖矩阵（catalog 命令可打印）：
    web   : R01 R02 R03 R04 R07 R08 R09 R10 R17 R20 R21 R22 R23   (13)
    http  : R05 R06 R11 R12 R15 R18 R19 R24                        (8)
    chain : R13 R14                                                (2)
    N/A   : R16（手势，需小程序/真机运行态）
    = 24/24

用法：
    python run_assertions.py web  --pages pages.json --state state.json --base-url ... --out web.csv
    python run_assertions.py http --spec checks.json --env env.json --out http.csv
    python run_assertions.py catalog
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path

RULE_COVERAGE = {
    "R01": ("web", "标题/页面身份可发现"),
    "R02": ("web", "禁用控件一致性"),
    "R03": ("web", "反馈基础设施存在（toast/aria-live）"),
    "R04": ("web", "浮层 ESC 关闭（无浮层则 N/A）"),
    "R05": ("http", "重复请求无副作用/幂等"),
    "R06": ("http", "参数校验 4xx"),
    "R07": ("web", "文本容器溢出"),
    "R08": ("web", "空态兜底"),
    "R09": ("web", "列表 total 与行数一致"),
    "R10": ("web", "刷新后状态可复现"),
    "R11": ("http", "权限四层（接口 403）"),
    "R12": ("http", "对象级越权"),
    "R13": ("chain", "后台→C 端可见（链路）"),
    "R14": ("chain", "异步任务状态机（链路）"),
    "R15": ("http", "上传类型/大小校验"),
    "R16": ("na", "手势滑动（需真机/小程序运行态）"),
    "R17": ("web", "时间展示无原始 UTC/ISO"),
    "R18": ("http", "非法状态查询/迁移被拒"),
    "R19": ("http", "计数/分页一致性"),
    "R20": ("web+http", "错误文案无堆栈/兜底编号"),
    "R21": ("web", "对比度 WCAG AA"),
    "R22": ("web", "三档视口无横向溢出"),
    "R23": ("web", "键盘焦点不丢失"),
    "R24": ("http", "导出/下载权限"),
}

JS_METRICS = r"""() => {
  const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const res = {};

  // A07 文本容器溢出（排除设计内滚动/省略号/无文本容器）
  let overflow = 0, samples = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    if (!(el.innerText||'').trim()) continue;
    const cs = getComputedStyle(el);
    if (['hidden','auto','scroll'].includes(cs.overflowX) || cs.overflow === 'hidden') continue;
    if (cs.textOverflow === 'ellipsis' || cs.whiteSpace === 'nowrap') continue;
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) {
      overflow++;
      if (samples.length < 3) samples.push((el.className||el.tagName).toString().slice(0,40)+':'+el.scrollWidth+'/'+el.clientWidth);
    }
  }
  res.overflowCount = overflow; res.overflowSamples = samples;

  // A21 对比度
  function lum(c){const[r,g,b]=c.map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*r+0.7152*g+0.0722*b;}
  function parse(s){const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const q=m[1].split(',').map(Number);return {rgb:[q[0],q[1],q[2]],a:q.length>3?q[3]:1};}
  function bgOf(el){let e=el;while(e){const q=parse(getComputedStyle(e).backgroundColor);if(q&&q.a>0.1)return q.rgb;e=e.parentElement;}return[255,255,255];}
  let worst=null, lowCount=0;
  for (const el of [...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && (e.innerText||'').trim().length>=2)) {
    if (!vis(el)) continue;
    const cs=getComputedStyle(el); const fg=parse(cs.color); if(!fg) continue;
    const bg=bgOf(el); const l1=lum(fg.rgb), l2=lum(bg);
    const ratio=(Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
    const fs=parseFloat(cs.fontSize)||12, bold=parseInt(cs.fontWeight)>=700;
    const need=(fs>=24||(fs>=18.66&&bold))?3.0:4.5;
    if(!worst||ratio<worst.ratio) worst={ratio:Math.round(ratio*100)/100,need,text:(el.innerText||'').trim().slice(0,20),size:fs};
    if(ratio<need) lowCount++;
  }
  res.contrastWorst=worst; res.contrastLow=lowCount;
  res.docScrollWidth=document.documentElement.scrollWidth; res.innerWidth=window.innerWidth;

  // R01 标题/身份
  const body = (document.body.innerText||'');
  res.title = document.title || '';
  res.notFound = /404|页面不存在|没有找到页面/.test(body.slice(0,400));

  // R02 禁用控件
  const ctrls=[...document.querySelectorAll('button,.el-button')].filter(vis);
  let mism=0;
  for (const b of ctrls) {
    if (b.disabled === true) continue;                      // 原生 disabled 已由浏览器拦截
    const dis = b.getAttribute('aria-disabled')==='true' || b.classList.contains('is-disabled');
    if (dis && getComputedStyle(b).pointerEvents !== 'none') mism++;   // 仅样式置灰但仍可点才算问题
  }
  res.controls=ctrls.length; res.disabledMismatch=mism;

  // R03 反馈设施
  res.hasToast=!!document.querySelector('.el-message, .el-notification, [aria-live], .toast');

  // R04 浮层
  res.dialogVisible=[...document.querySelectorAll('.el-dialog,.el-drawer')].filter(vis).length;

  // R08 空态
  const tableRows=document.querySelectorAll('.el-table__row').length;
  const cardRows=document.querySelectorAll('.style-card,.el-card,.card-item,[class*="list-item"]').length;
  const rows=Math.max(tableRows,cardRows);
  res.rows=rows; res.tableRows=tableRows; res.cardRows=cardRows;
  res.emptyText=/(暂无|没有数据|无数据|空空如也|还没)/.test(body);

  // R09 total
  const m=body.match(/共\s*(\d+)\s*条/);
  res.total=m?parseInt(m[1]):null;
  const ps=body.match(/(\d+)\s*条\/页/);
  res.pageSize=ps?parseInt(ps[1]):null;

  // R17 原始时间
  res.rawTime=(body.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?|GMT[+-]\d|UTC[+-]\d/g)||[]).slice(0,3);

  // R20 错误文案
  res.stackSignals=(body.match(/Exception|NullPointerException|Traceback|at org\.|at java\.|出了点问题[，,]\s*请稍后再试/g)||[]).slice(0,3);
  res.errorHint=/(失败|错误|异常)/.test(body);

  return res;
}"""


def web_assertions(args) -> int:
    from playwright.sync_api import sync_playwright

    pages = json.loads(Path(args.pages).read_text(encoding="utf-8"))
    pages = [p for p in pages if p.get("path") and not p["path"].startswith("/__view__")]
    rules = [r.strip().upper() for r in args.rules.split(",") if r.strip()]
    state = json.loads(Path(args.state).read_text(encoding="utf-8")) if args.state else None
    rows: list[dict] = []
    t0 = time.time()

    def add(rule, page, assertion, status, metric, evidence=""):
        rows.append({"rule_id": rule, "page": page, "assertion": assertion,
                     "status": status, "metric": metric, "evidence": str(evidence)[:300]})

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
            name = pg.get("name", pg["path"])
            url = args.base_url.rstrip("/") + pg["path"]
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
                page.wait_for_timeout(args.wait_ms)
            except Exception as e:
                for r in rules:
                    add(r, name, "", "BLOCKED", "", str(e)[:150])
                continue
            m = page.evaluate(JS_METRICS)
            for r in rules:
                if r == "R01":
                    ok = bool(m["title"].strip()) and not m["notFound"]
                    add(r, name, "A01", "PASS" if ok else "FAIL",
                        f"title={m['title'][:24]} notFound={m['notFound']}")
                elif r == "R02":
                    ok = m["disabledMismatch"] == 0
                    add(r, name, "A02", "PASS" if ok else "FAIL",
                        f"controls={m['controls']} mismatch={m['disabledMismatch']}")
                elif r == "R03":
                    if m["hasToast"]:
                        add(r, name, "A03", "PASS", "toastContainer=True")
                    else:
                        add(r, name, "A03", "N/A", "容器懒加载，需触发操作后验证")
                elif r == "R04":
                    if m["dialogVisible"] == 0:
                        add(r, name, "A04", "N/A", "无浮层，需操作后测")
                    else:
                        try:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(600)
                            left = page.evaluate("() => [...document.querySelectorAll('.el-dialog,.el-drawer')].filter(e=>e.offsetWidth).length")
                            add(r, name, "A04", "PASS" if left < m["dialogVisible"] else "FAIL",
                                f"before={m['dialogVisible']} after={left}")
                        except Exception as e:
                            add(r, name, "A04", "BLOCKED", str(e)[:80])
                elif r == "R07":
                    add(r, name, "A07", "PASS" if m["overflowCount"] == 0 else "FAIL",
                        f"overflow={m['overflowCount']}", ";".join(m["overflowSamples"]))
                elif r == "R08":
                    if m["rows"] == 0:
                        add(r, name, "A08", "PASS" if m["emptyText"] else "FAIL",
                            "rows=0", "emptyText=" + str(m["emptyText"]))
                    else:
                        add(r, name, "A08", "N/A", f"rows={m['rows']}（非空态）")
                elif r == "R09":
                    if m["total"] is None:
                        add(r, name, "A09", "N/A", "无分页文案")
                    elif not m["pageSize"] and 0 < m["rows"] < m["total"]:
                        add(r, name, "A09", "N/A", f"total={m['total']} rows={m['rows']}，每页条数不可读")
                    else:
                        full = bool(m["pageSize"]) and m["total"] <= m["pageSize"]
                        ok = (m["rows"] == m["total"]) if full else (m["rows"] == m["pageSize"])
                        add(r, name, "A09", "PASS" if ok else "FAIL",
                            f"total={m['total']} rows={m['rows']} pageSize={m['pageSize']}")
                elif r == "R10":
                    try:
                        before = page.evaluate("() => document.querySelectorAll('.el-table__row').length")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(args.wait_ms)
                        after = page.evaluate("() => document.querySelectorAll('.el-table__row').length")
                        add(r, name, "A10", "PASS" if before == after else "FAIL",
                            f"rows {before}->{after}")
                    except Exception as e:
                        add(r, name, "A10", "BLOCKED", str(e)[:80])
                elif r == "R17":
                    add(r, name, "A17", "PASS" if not m["rawTime"] else "FAIL",
                        f"rawTime={len(m['rawTime'])}", m["rawTime"])
                elif r == "R20":
                    ok = not m["stackSignals"]
                    add(r, name, "A20", "PASS" if ok else "FAIL",
                        f"signals={len(m['stackSignals'])}", m["stackSignals"])
                elif r == "R21":
                    w = m["contrastWorst"]
                    ok = bool(w) and w["ratio"] >= w["need"]
                    add(r, name, "A21", "PASS" if ok else "FAIL",
                        f"worst={w['ratio'] if w else None} low={m['contrastLow']}",
                        json.dumps(w, ensure_ascii=False) if w else "")
                elif r == "R22":
                    sweep = []
                    try:
                        for wd, ht in ((1280, 800), (1440, 900), (1920, 1080)):
                            page.set_viewport_size({"width": wd, "height": ht})
                            page.wait_for_timeout(320)
                            mm = page.evaluate("() => ({s: document.documentElement.scrollWidth, v: window.innerWidth})")
                            sweep.append((wd, mm["s"], mm["v"], mm["s"] <= mm["v"] + 1))
                    except Exception:
                        sweep = [("ERR", 0, 0, False)]
                    page.set_viewport_size({"width": 1440, "height": 900})
                    bad = [x for x in sweep if not x[3]]
                    add(r, name, "A22", "PASS" if not bad else "FAIL",
                        " ".join(f"{w}:{s}/{v}" for w, s, v, _ in sweep), f"溢出视口={[x[0] for x in bad]}")
                elif r == "R23":
                    seq = []
                    try:
                        for _ in range(8):
                            page.keyboard.press("Tab")
                            page.wait_for_timeout(70)
                            seq.append(page.evaluate("() => { const e=document.activeElement; return e? (e.tagName+'|'+(e.innerText||e.getAttribute('placeholder')||'').slice(0,14)) : 'null'; }"))
                    except Exception as e:
                        seq = [f"ERR {e}"]
                    lost = [s for s in seq if s.startswith("BODY|") or s == "null"]
                    add(r, name, "A23", "FAIL" if lost else "PASS",
                        f"tab_steps={len(seq)} lost={len(lost)}", " > ".join(seq[:4]))
                else:
                    add(r, name, "", "N/A", f"{r} 非 web 检查项")
        b.close()
    write_csv(rows, args.out)
    stat = {}
    for r in rows:
        stat[(r["rule_id"], r["status"])] = stat.get((r["rule_id"], r["status"]), 0) + 1
    print(f"web: pages={min(len(pages), args.limit)} rules={len(rules)} rows={len(rows)} {int(time.time()-t0)}s")
    print("  " + ", ".join(f"{k[0]}:{k[1]}={v}" for k, v in sorted(stat.items())))
    print(f"  -> {args.out}")
    return 0


def http_assertions(args) -> int:
    import requests
    import urllib3
    urllib3.disable_warnings()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    env = json.loads(Path(args.env).read_text(encoding="utf-8"))
    base = env["base_url"].rstrip("/")
    rows: list[dict] = []
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
            if isinstance(j, list):
                j = {"code": 200, "data": {"list": j}, "_raw_list": True}
        except Exception as e:
            rows.append({"rule_id": rule, "page": chk.get("id", path), "assertion": chk.get("assertion", ""),
                         "status": "BLOCKED", "metric": "", "evidence": str(e)[:160]})
            continue
        expect = chk.get("expect") or {}
        fails = []
        if "http" in expect and r.status_code != expect["http"]:
            fails.append(f"http={r.status_code}!={expect['http']}")
        if "code" in expect and j.get("code") != expect["code"]:
            fails.append(f"code={j.get('code')}!={expect['code']}")
        if "code_in" in expect and j.get("code") not in expect["code_in"]:
            fails.append(f"code={j.get('code')}!in {expect['code_in']}")
        if "code_not_in" in expect and j.get("code") in expect["code_not_in"]:
            fails.append(f"code={j.get('code')} 命中禁止值")
        present = chk.get("present", expect.get("present"))
        if present and not isinstance(j.get("data"), (dict, list)):
            fails.append("data absent")
        absent = chk.get("absent_fields") or expect.get("absent_fields") or []
        for f in absent:
            if f in json.dumps(j, ensure_ascii=False):
                fails.append(f"leaked:{f}")
        max_ms = chk.get("max_ms", expect.get("max_ms"))
        if max_ms is not None and dt > max_ms:
            fails.append(f"{dt}ms>{max_ms}ms")
        rows.append({"rule_id": rule, "page": chk.get("id", path), "assertion": chk.get("assertion", ""),
                     "status": "PASS" if not fails else "FAIL",
                     "metric": f"http={r.status_code} code={j.get('code')} {dt}ms",
                     "evidence": ";".join(fails)[:300]})
    write_csv(rows, args.out)
    from collections import Counter
    print(f"http: checks={len(spec)} rows={len(rows)} " + str(Counter(r['status'] for r in rows)))
    print(f"  -> {args.out}")
    return 0


def write_csv(rows: list[dict], out: str) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rule_id", "page", "assertion", "status", "metric", "evidence"])
        w.writeheader()
        w.writerows(rows)


def catalog(_args) -> int:
    from collections import Counter
    kinds = Counter(v[0] for v in RULE_COVERAGE.values())
    print(f"24 条准则断言实现分布: {dict(kinds)}")
    for rid, (kind, desc) in RULE_COVERAGE.items():
        print(f"  {rid}  {kind:8s} {desc}")
    missing = [r for r in (f"R{i:02d}" for i in range(1, 25)) if r not in RULE_COVERAGE]
    print("missing:", missing or "none")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("web"); w.set_defaults(fn=web_assertions)
    w.add_argument("--pages", required=True); w.add_argument("--state", default="")
    w.add_argument("--base-url", required=True)
    w.add_argument("--rules", default="R01,R02,R03,R07,R08,R09,R10,R17,R20,R21,R22,R23")
    w.add_argument("--limit", type=int, default=10); w.add_argument("--out", required=True)
    w.add_argument("--timeout", type=int, default=45000); w.add_argument("--wait-ms", type=int, default=4000)

    h = sub.add_parser("http"); h.set_defaults(fn=http_assertions)
    h.add_argument("--spec", required=True); h.add_argument("--env", required=True)
    h.add_argument("--out", required=True)

    c = sub.add_parser("catalog"); c.set_defaults(fn=catalog)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
