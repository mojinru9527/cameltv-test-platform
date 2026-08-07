"""体育平台承接 — 交互路径拓扑图生成（Batch 114，C113-1）。

消费 evidence/batch-113/interaction-paths.json（3172 条「页面→入口→目标页」边），
按模块聚合为拓扑 nodes/edges（入口合并 + P0 标记），输出 JSON 与 mermaid 文档。

运行: <venv-python> scripts/sports/build-interaction-topology.py
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PATHS = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-113" / "interaction-paths.json"
OUT_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-114"
DOC = REPO_ROOT / "test-platform-v2" / "docs" / "体育平台-交互拓扑.md"

P0_MODULES = {"首页", "赛事详情", "直播间", "资讯", "搜索", "我的", "联赛", "球队", "回放", "世界杯专题"}


def main() -> int:
    if not PATHS.exists():
        print("ERROR: 缺 interaction-paths.json（先跑 batch-113 generate-interaction-cases.py）", flush=True)
        return 1
    data = json.loads(PATHS.read_text(encoding="utf-8"))
    paths = data.get("paths", [])

    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    for p in paths:
        f = p.get("from_module") or "未知"
        t = p.get("to") or ""
        # 目标模块：按 to 路径 label 归类
        to_mod = _infer_module(t)
        nodes.setdefault(f, {"id": f, "p0": f in P0_MODULES, "pages": set()})
        nodes.setdefault(to_mod, {"id": to_mod, "p0": to_mod in P0_MODULES, "pages": set()})
        if p.get("from"):
            nodes[f]["pages"].add(p["from"])
        nodes[to_mod]["pages"].add(t)
        key = (f, to_mod)
        e = edges.setdefault(key, {"from": f, "to": to_mod, "entries": set(), "count": 0})
        if p.get("entry"):
            e["entries"].add(p["entry"])
        e["count"] += 1

    node_list = [
        {"id": n["id"], "p0": n["p0"], "pages": sorted(n["pages"])[:20], "page_count": len(n["pages"])}
        for n in nodes.values()
    ]
    edge_list = [
        {"from": e["from"], "to": e["to"], "entries": sorted(e["entries"])[:20],
         "entry_count": len(e["entries"]), "count": e["count"],
         "p0": e["from"] in P0_MODULES and e["to"] in P0_MODULES}
        for e in edges.values()
    ]
    edge_list.sort(key=lambda x: (-x["count"], x["from"], x["to"]))
    node_list.sort(key=lambda x: (-x["p0"], x["id"]))

    topology = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(PATHS.relative_to(REPO_ROOT)),
        "stats": {"edges_raw": len(paths), "nodes": len(node_list), "edges": len(edge_list),
                  "p0_nodes": sum(1 for n in node_list if n["p0"]),
                  "p0_edges": sum(1 for e in edge_list if e["p0"])},
        "nodes": node_list,
        "edges": edge_list,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "interaction-topology.json").write_text(
        json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # mermaid 文档
    mermaid_lines = ["```mermaid", "flowchart TD"]
    for n in node_list:
        cls = "P0" if n["p0"] else "P1"
        mermaid_lines.append(f'  {n["id"]}["{n["id"]}"]:::{cls}')
    for e in edge_list:
        if e["p0"] and e["count"] >= 3:
            mermaid_lines.append(f'  {e["from"]} -->|"{e["entry_count"]} 入口/{e["count"]} 边"| {e["to"]}')
    mermaid_lines.append("```")
    DOC.write_text(
        "---\ntitle: 体育平台-交互拓扑\nowner: qa-team\nlast_reviewed: 2026-08-07\nstatus: active\n"
        "tags: [sports-platform, interaction, topology]\n---\n\n"
        "# 体育平台-交互拓扑（Batch 114，C113-1）\n\n"
        f"> 来源：production-pages.json links（batch-110 勘察）→ 3172 条边 → 模块级拓扑。\n"
        f"> 统计：节点 {len(node_list)}（P0 {sum(1 for n in node_list if n['p0'])}）/ "
        f"边 {len(edge_list)}（P0 {sum(1 for e in edge_list if e['p0'])}）。\n\n"
        "## 模块拓扑（P0 高亮，边显示入口数与边数）\n\n"
        + "\n".join(mermaid_lines) + "\n\n"
        "## 关键闭环\n\n"
        "- 首页 → 赛事详情 → 直播间（观看直播）→ 返回首页\n"
        "- 首页 → 回放列表 → 回放详情（播放器）\n"
        "- 资讯列表 → 资讯详情 → 相关推荐\n"
        "- 搜索 → 搜索结果 → 详情页\n"
        "- 联赛 → 球队 → 赛事详情\n\n"
        "## 数据\n\n"
        "`evidence/batch-114/interaction-topology.json`（nodes/edges/入口聚合/P0 标记）。\n",
        encoding="utf-8",
    )
    print(f"[topology] raw={len(paths)} nodes={len(node_list)} edges={len(edge_list)} p0n={sum(1 for n in node_list if n['p0'])} p0e={sum(1 for e in edge_list if e['p0'])}")
    print(f"[doc] {DOC.relative_to(REPO_ROOT)}")
    return 0


def _infer_module(path: str) -> str:
    p = path.lower()
    rules = [
        ("/live", "直播间"), ("/animation", "直播间"),
        ("/football/", "赛事详情"), ("/match-replay", "回放"),
        ("/news/", "资讯"), ("/q/news", "资讯"),
        ("/search", "搜索"), ("/my", "我的"),
        ("/r/league", "联赛"), ("/league/", "联赛"),
        ("/team/", "球队"), ("/worldcup", "世界杯专题"),
        ("/register", "登录注册"), ("/help", "通用"), ("/setting", "通用"),
    ]
    for frag, mod in rules:
        if frag in p:
            return mod
    return "其他页面"


if __name__ == "__main__":
    raise SystemExit(main())
