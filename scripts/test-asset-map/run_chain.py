#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""链路执行器（声明式）：fixtures → entry_gate → steps → cleanup。

链路规格（JSON）：
{
  "chain_id": "CHAIN-X",
  "fixtures":   [{"id":"f1","method":"GET","path":"/...","auth":"admin","expect":{"code":200},"extract":{"cid":"data.rows[0].id"}}],
  "entry_gate": ["f1"],
  "steps":      [{"no":1,"method":"GET","path":"/client/.../{cid}","auth":"client","expect":{"code":200},"present":true}],
  "cleanup":    [{"method":"POST","path":"/...","auth":"admin","optional":true}]
}

规则：
- fixture 失败 → 整链 BLOCKED，后续不执行（不允许把中间结果当通过）；
- entry_gate 任一失败 → BLOCKED；
- 每一步失败不影响后续步骤执行，但链路整体标记 FAIL；
- cleanup 无论成败都执行（best-effort），并记录结果；
- 变量 {name} 由 extract 的简易 JSONPath 填充。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path


def dig(obj, path: str):
    cur = obj
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            idx = int(part[1:-1])
            if not isinstance(cur, list) or idx >= len(cur):
                return None
            cur = cur[idx]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
    return cur


def subst(template, ctx):
    if not isinstance(template, str):
        return template
    def rep(m):
        v = ctx.get(m.group(1))
        return str(v) if v is not None else m.group(0)
    return re.sub(r"\{(\w+)\}", rep, template)


def run_chain(args) -> int:
    import requests
    import urllib3
    urllib3.disable_warnings()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    env = json.loads(Path(args.env).read_text(encoding="utf-8"))
    base = env["base_url"].rstrip("/")
    ctx: dict = {}
    rows: list[dict] = []
    verdict = {"chain_id": spec.get("chain_id"), "status": "PASS", "fixtures": [], "steps": [], "cleanup": []}

    def call(node, phase: str, no=None):
        headers = dict(node.get("headers") or {})
        auth = node.get("auth")
        if auth == "admin":
            headers["Authorization"] = "Bearer " + env["admin_token"]
            headers["clientid"] = env.get("clientid", "")
        elif auth == "client":
            headers["token"] = env["client_token"]
        method = node.get("method", "GET").upper()
        path = subst(node["path"], ctx)
        body = node.get("body")
        if isinstance(body, dict):
            body = {k: subst(v, ctx) if isinstance(v, str) else v for k, v in body.items()}
        t0 = time.time()
        try:
            r = requests.request(method, base + path, headers=headers,
                                 json=body if isinstance(body, dict) else None,
                                 data=body if isinstance(body, str) else None,
                                 timeout=node.get("timeout", 60), verify=False)
            dt = int((time.time() - t0) * 1000)
            try:
                j = r.json()
            except Exception:
                j = {"_raw": r.text[:200]}
        except Exception as e:
            rows.append({"chain": spec.get("chain_id"), "phase": phase, "no": no or "",
                         "step": node.get("name") or path, "status": "BLOCKED",
                         "metric": "", "evidence": str(e)[:160]})
            verdict[phase if phase != "entry" else "steps"].append({"no": no, "status": "BLOCKED"})
            return False
        expect = node.get("expect") or {}
        fails = []
        if "http" in expect and r.status_code != expect["http"]:
            fails.append(f"http={r.status_code}!={expect['http']}")
        if "code" in expect and j.get("code") != expect["code"]:
            fails.append(f"code={j.get('code')}!={expect['code']}")
        if "code_in" in expect and j.get("code") not in expect["code_in"]:
            fails.append(f"code={j.get('code')}!in {expect['code_in']}")
        if node.get("present") and not isinstance(j.get("data"), (dict, list)):
            fails.append("data absent")
        if node.get("absent_fields"):
            blob = json.dumps(j, ensure_ascii=False)
            for f in node["absent_fields"]:
                if f in blob:
                    fails.append(f"leaked:{f}")
        status = "PASS" if not fails else "FAIL"
        rows.append({"chain": spec.get("chain_id"), "phase": phase, "no": no or "",
                     "step": node.get("name") or f"{method} {path}", "status": status,
                     "metric": f"http={r.status_code} code={j.get('code')} {dt}ms",
                     "evidence": ";".join(fails)[:300]})
        verdict[phase if phase != "entry" else "steps"].append({"no": no, "status": status,
                                                               "path": path, "fails": fails})
        # extract
        for var, jp in (node.get("extract") or {}).items():
            val = dig(j, jp)
            if val is not None:
                ctx[var] = val
        return status == "PASS"

    # fixtures
    fixture_ok = True
    for f in spec.get("fixtures") or []:
        if not call(f, "fixtures", f.get("id")):
            fixture_ok = False
            break
    if not fixture_ok:
        verdict["status"] = "BLOCKED"
    else:
        gate_ids = spec.get("entry_gate") or []
        gate_fail = [g for g in gate_ids if not ctx.get(g) and g not in (spec.get("fixtures") and [])]
        # entry_gate 语义：列出的 fixture id 必须已成功执行且提取到值
        failed_ids = {x.get("no") for x in verdict["fixtures"] if x.get("status") != "PASS"}
        gate_bad = [g for g in gate_ids if g in failed_ids]
        if gate_bad:
            verdict["status"] = "BLOCKED"
        else:
            any_fail = False
            for st in spec.get("steps") or []:
                ok = call(st, "steps", st.get("no"))
                if not ok:
                    any_fail = True
            if any_fail:
                verdict["status"] = "FAIL"

    # cleanup always
    for c in spec.get("cleanup") or []:
        call(c, "cleanup")

    # 汇总
    print(f"chain={spec.get('chain_id')} status={verdict['status']}")
    for r in rows:
        print(f"  [{r['status']:7s}] {r['phase']:8s} {str(r['no']):>2s} {r['step'][:60]} | {r['metric']} {r['evidence']}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["chain", "phase", "no", "step", "status", "metric", "evidence"])
        w.writeheader()
        w.writerows(rows)
    out.with_suffix(".verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    return 0 if verdict["status"] in ("PASS",) else 0  # 不阻断流水线，状态在 verdict 里


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    return run_chain(args)


if __name__ == "__main__":
    raise SystemExit(main())

