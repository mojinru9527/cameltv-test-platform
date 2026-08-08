"""Batch 123 — 体育模块关联图谱入库（从 Batch 122 用例结构计算实体+关系）。

读取 `work-logs/evidence/batch-122/cases/**/*.json`（编写格式），展开后计算：
- 实体：module（入口/一级[/二级]）、test_case、api
- 关系：contains（模块层级/模块含用例）、tested_by（接口被用例覆盖）、
        navigates_to（用户端模块跳转）、links_to_admin（用户端↔运营后台）、
        configures（konfi 配置影响用户端）
POST 到 `/knowledge/graph/module-associations`（幂等）。

运行: TP_ADMIN_PASSWORD=<pwd> <python> scripts/knowledge/import-module-associations.py [--backend-url <url>] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx

ENTRANCES = {"安卓iOS": "AND", "PC-web": "PC", "移动端-web": "WEB", "运营后台": "ADM", "konfi": "KON"}
USERNAME = "sportsadmin"


def iter_case_files(path: Path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*.json")):
        yield p


def expand(case: dict) -> list[dict]:
    out = []
    if case.get("domain") == "体育-接口测试":
        out.append({**case, "_platform": "接口"})
        return out
    base = case.get("case_id", "")
    module = str(case.get("module", "")).strip("/")
    for pf in case.get("platforms") or []:
        code = ENTRANCES.get(pf)
        if not code:
            continue
        item = dict(case)
        item["module"] = f"{pf}/{module}"
        if base.startswith("SP-"):
            item["case_id"] = f"SP-{code}-{base[3:]}"
        item["_platform"] = pf
        out.append(item)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(Path(__file__).resolve().parents[1] / "work-logs" / "evidence" / "batch-122" / "cases"))
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cases: list[dict] = []
    for fp in iter_case_files(Path(args.cases)):
        data = json.loads(fp.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        for c in items:
            cases.extend(expand(c))
    print(f"[assoc] 展开用例 {len(cases)} 条", flush=True)

    # ── 实体 ──
    entities: dict[str, dict] = {}
    rels: list[dict] = []
    seen_rel: set[tuple[str, str, str]] = set()

    def ensure_entity(etype: str, key: str, name: str, desc: str = "", meta: dict | None = None):
        if key not in entities:
            entities[key] = {"entity_type": etype, "entity_key": key, "name": name,
                             "description": desc, "confidence": 1.0, "metadata": meta or {}}

    def add_rel(fk: str, rtype: str, tk: str, evidence: str = ""):
        if not fk or not tk:
            return
        sig = (fk, rtype, tk)
        if sig in seen_rel:
            return
        seen_rel.add(sig)
        rels.append({"from_key": fk, "relation_type": rtype, "to_key": tk, "confidence": 1.0, "evidence": evidence})

    # 模块路径 → 末段名 索引（用于 关联: 标签解析）
    by_last: dict[str, list[str]] = defaultdict(list)
    module_paths: dict[str, str] = {}

    for case in cases:
        cid = case["case_id"]
        path = case["module"]
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2:
            continue
        entrance, first = parts[0], parts[1]
        second = parts[2] if len(parts) >= 3 else ""
        key_parent = f"module:{entrance}/{first}"
        module_paths.setdefault(key_parent, f"{entrance}/{first}")
        by_last[first].append(key_parent)
        ensure_entity("module", key_parent, f"{entrance}/{first}",
                      f"入口 {entrance} · 一级模块 {first}", {"entrance": entrance})
        tcid = f"test_case:{cid}"
        ensure_entity("test_case", tcid, case.get("title", cid), path, {"module": path})
        if second:
            key_child = f"module:{entrance}/{first}/{second}"
            module_paths.setdefault(key_child, path)
            by_last[second].append(key_child)
            ensure_entity("module", key_child, path,
                          f"入口 {entrance} · {first}/{second}", {"entrance": entrance})
            add_rel(key_parent, "contains", key_child, f"case:{cid}")
            add_rel(key_child, "contains", tcid, f"case:{cid}")
        else:
            add_rel(key_parent, "contains", tcid, f"case:{cid}")
        # API 用例 → 接口实体 + tested_by
        if case.get("case_type") == "api" and case.get("api_endpoint"):
            ep = str(case["api_endpoint"]).split("?")[0]
            method = (case.get("api_method") or "GET").upper()
            akey = f"api:{method}:{ep}"
            ensure_entity("api", akey, ep, f"{method} {ep}")
            add_rel(akey, "tested_by", tcid, f"case:{cid}")

    # ── 关联: 标签 → 关系 ──
    for case in cases:
        cid = case["case_id"]
        path = case["module"]
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2:
            continue
        entrance = parts[0]
        src_key = f"module:{path}"
        if src_key not in module_paths:
            # 一级模块自身（无二级）
            src_key = f"module:{entrance}/{parts[1]}"
        if src_key not in module_paths:
            continue
        for tag in case.get("tags") or []:
            t = str(tag)
            if not t.startswith("关联:"):
                continue
            target_name = t[len("关联:"):]
            if target_name in ("运营后台", "konfi"):
                continue
            # 解析目标模块：同入口下末段名匹配；用户端跨三入口
            candidates = by_last.get(target_name, [])
            if entrance == "运营后台":
                for tk in candidates:
                    if tk.startswith("安卓iOS/") or tk.startswith("PC-web/") or tk.startswith("移动端-web/"):
                        add_rel(tk, "links_to_admin", src_key, f"case:{cid} tag:{t}")
            elif entrance == "konfi":
                for tk in candidates:
                    if tk.startswith("安卓iOS/") or tk.startswith("PC-web/") or tk.startswith("移动端-web/"):
                        add_rel(src_key, "configures", tk, f"case:{cid} tag:{t}")
            else:
                pref = f"module:{entrance}/"
                for tk in candidates:
                    if tk.startswith(pref):
                        add_rel(src_key, "navigates_to", tk, f"case:{cid} tag:{t}")

    print(f"[assoc] 实体 {len(entities)} 关系 {len(rels)}", flush=True)
    if args.dry_run:
        return 0
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    payload = {"entities": list(entities.values()), "relations": rels}
    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=180,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as client:
        r = client.post("/auth/login", json={"username": USERNAME, "password": args.password})
        r.raise_for_status()
        client.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
        rr = client.post("/knowledge/graph/module-associations", json=payload)
        rr.raise_for_status()
        print("[assoc] result:", json.dumps(rr.json().get("data", {}), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
