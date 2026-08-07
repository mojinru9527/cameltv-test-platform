"""体育平台承接 — 知识中心关联基座入库与检索验证（Batch 113，C112-1）。

把「体育平台-关联基座.json」（module→function→interface→backend→konfi）转为 Markdown 章节，
经 /knowledge/capture 入库（C110-2 已验证通道），再用 /knowledge/search 检索关键模块/接口/配置项
验证命中，证据落盘。

运行: <venv-python> scripts/sports/sync-association-knowledge.py --password "$env:TP_ADMIN_PASSWORD"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "test-platform-v2" / "docs" / "体育平台-关联基座.json"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-113"


def _baseline_markdown(data: dict) -> str:
    """把关联基座转成结构化 Markdown（供知识中心入库与 RAG 检索）。"""
    lines = ["# 体育平台模块-接口-功能关联基座", "",
             "> 来源：功能模块地图 v2 + evidence/batch-110 生产实测。",
             "> 用途：用例生成前先按关联关系定位模块/接口/功能，避免遗漏。", ""]
    lines.append("## 用户端功能模块（13）")
    for m in data.get("user_modules", []):
        lines.append(f"### {m['module']}")
        if m.get("page"):
            lines.append(f"- 生产页面：{m['page']}")
        if m.get("interfaces_raw"):
            lines.append(f"- 生产接口：{m['interfaces_raw']}")
        if m.get("backend"):
            lines.append(f"- 运营后台：{m['backend']}")
        if m.get("konfi"):
            lines.append(f"- konfi：{m['konfi']}")
        lines.append("")
    lines.append("## 运营后台功能模块（15）")
    for m in data.get("admin_modules", []):
        lines.append(f"### {m['module']}")
        if m.get("pages"):
            lines.append(f"- 生产菜单：{m['pages']}")
        if m.get("case_domain"):
            lines.append(f"- 平台用例域：{m['case_domain']}")
        lines.append("")
    lines.append("## konfi 配置项关联")
    for link in data.get("konfi_links", []):
        keys = "、".join(f"`{k}`" for k in link.get("form_keys", []))
        lines.append(f"- {link['function']}：{keys}（记录数 {link.get('record_counts', '')}）")
    lines.append("")
    lines.append("## 接口-功能模块映射")
    for it in data.get("interface_map", []):
        lines.append(f"- {it['module']}：{it['method']} `{it['path']}`（参数：{it.get('sample_params', '')}）")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1
    if not BASELINE.exists():
        print("ERROR: 关联基座缺失，先运行 build-association-baseline.py", flush=True)
        return 1

    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    content = _baseline_markdown(data)
    summary: dict = {}

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=180,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        # 1) capture 关联基座
        cap = c.post("/knowledge/capture", json={
            "title": "体育平台-模块-接口-功能关联基座（Batch 113）",
            "content": content,
            "source_url": "https://github.com/mojinru9527/cameltv-test-platform/blob/main/test-platform-v2/docs/体育平台-关联基座.json",
            "tags": ["sports-platform", "association-baseline", "batch-113"],
        })
        cap_body = cap.json()
        print(f"[capture] code={cap_body.get('code')} data={cap_body.get('data')}", flush=True)
        summary["capture"] = {"http": cap.status_code, "body": cap_body}

        # 2) sources 可见
        srcs = c.get("/knowledge/sources", params={"page_size": 100}).json().get("data", {})
        items = srcs.get("items") or []
        matched = [s for s in items if "关联基座" in str(s.get("title") or "")]
        summary["sources"] = {
            "total": srcs.get("total"),
            "matched": [{"id": s.get("id"), "title": s.get("title"), "status": s.get("status")} for s in matched],
        }
        print(f"[sources] total={srcs.get('total')} matched={len(matched)}", flush=True)

        # 3) RAG 检索命中
        queries = [
            "sports_live_hot_competition",
            "/camel-service/ee/sports_live/hot_match",
            "世界杯专题",
            "热门联赛",
            "运营后台-直播管理",
        ]
        hits: dict = {}
        for q in queries:
            sr = c.post("/knowledge/search", json={"query": q, "top_k": 5, "mode": "hybrid"})
            res = sr.json().get("data") or []
            hits[q] = [
                {"source": x.get("source_name"), "title": x.get("title"), "score": x.get("score"),
                 "snippet": str(x.get("snippet") or "")[:120]}
                for x in res[:3]
            ]
            print(f"[search] '{q}' -> {len(res)} hits", flush=True)
        summary["search"] = hits

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "knowledge-association-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
