# -*- coding: utf-8 -*-
"""体育模块基座用例生成（Batch 125 / Slice 3）。

链路验证：功能梳理清单(功能点) + 页面需求文本 + 生产发现 → ai_service.generate_test_cases
（内部加载 功能用例规范 skill 权威输出要求 + 深度用例补充层）→ 输出基础用例 JSON。

用法:
    python scripts/run_base_case_generation.py --module "运营后台/赛事预测" [--limit-pages 3] [--out ...]
    python scripts/run_base_case_generation.py --module "用户端/赛事详情" --pick 预测Pick
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

# 允许从主工作区 .env 读取 DeepSeek Key（本地开发验证）
MAIN_ENV = Path(r"F:\CamelTv\test-platform-v2\backend\.env")
if MAIN_ENV.exists():
    for line in MAIN_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
INVENTORY = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "sports-feature-inventory.json"
EXPORT_BASE = Path(r"F:\CamelTv\test-platform-v2\backend\data\lanhu-exports")
PROD_FINDINGS = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "production-findings.json"
OUT_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "base-cases"


def extract_page_text(html_path: Path) -> str:
    import html as html_mod
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    return html_mod.unescape(raw)


def compose_module_content(module_path: str, pick: str = "") -> str:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    export_label = module_path.split("/")[0]
    module_name = module_path.split("/")[1] if "/" in module_path else module_path
    exports = inv["exports"]
    if export_label not in exports:
        raise ValueError(f"未知入口 {export_label}，可用: {list(exports.keys())}")
    mod = next((m for m in exports[export_label]["modules"] if m["name"] == module_name), None)
    if not mod:
        raise ValueError(f"模块 {module_name} 不在 {export_label}，可用: {[m['name'] for m in exports[export_label]['modules']]}")
    export_dir = EXPORT_BASE / (export_label + "原型")
    parts = [f"# 体育平台-{export_label}-{module_name} 需求与功能点\n"]
    pages = []
    for p in mod["pages"]:
        if pick and pick not in p["name"] and pick not in " ".join(f["text"] for f in p["function_points"]):
            continue
        pages.append(p)
        parts.append(f"\n## 页面：{p['name']}（{p['path']}）")
        parts.append("### 功能点")
        for fp in p["function_points"][:40]:
            parts.append(f"- [{fp['type']}] {fp['text']}")
        html_path = export_dir / p["lanhu_page_id"]
        if html_path.exists():
            txt = extract_page_text(html_path)
            parts.append("### 页面内容")
            parts.append(txt[:3000])
    # 生产发现补充（如有）
    if PROD_FINDINGS.exists():
        pf = json.loads(PROD_FINDINGS.read_text(encoding="utf-8"))
        for page in pf.get("pages", []):
            if any(k in page["page"] for k in ["赛事详情", "预测", "联赛", "球队", "球员", "直播", "个人中心", "资讯"]):
                parts.append(f"\n## 生产深度体验（{page['page']}）")
                parts.append("\n".join(page.get("findings", page.get("modules", []))))
    return "\n".join(parts)


def build_extraction(module_path: str, pick: str = "") -> tuple[dict, str]:
    """从功能清单构造 extraction（模块×功能点），并拼装原始需求文本。"""
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    export_label = module_path.split("/")[0]
    module_name = module_path.split("/")[1] if "/" in module_path else module_path
    exports = inv["exports"]
    if export_label not in exports:
        raise ValueError(f"未知入口 {export_label}，可用: {list(exports.keys())}")
    mod = next((m for m in exports[export_label]["modules"] if m["name"] == module_name), None)
    if not mod:
        raise ValueError(f"模块 {module_name} 不在 {export_label}")
    export_dir = EXPORT_BASE / (export_label + "原型")
    modules = []
    raw_parts = [f"# 体育平台-{export_label}-{module_name} 需求与功能点"]
    for p in mod["pages"]:
        if pick and pick not in p["name"] and pick not in " ".join(f["text"] for f in p["function_points"]):
            continue
        fps = []
        for i, fp in enumerate(p["function_points"][:30], start=1):
            fps.append({
                "id": f"FP-{p['name'][:4]}-{i:02d}",
                "title": fp["text"],
                "description": f"{fp['type']}：{fp['text']}（页面 {p['name']}）",
                "type": "functional",
                "client_scope": ["安卓iOS", "PC-web", "移动端-web"] if export_label == "用户端" else ["运营后台"],
            })
        modules.append({
            "id": p["path"],
            "name": f"{export_label}/{module_name}/{p['name']}",
            "description": f"页面 {p['name']}（{p['lanhu_page_id']}）功能点",
            "function_points": fps,
        })
        raw_parts.append(f"\n## 页面 {p['name']} 功能点")
        for fp in fps:
            raw_parts.append(f"- {fp['title']}")
        html_path = export_dir / p["lanhu_page_id"]
        if html_path.exists():
            txt = extract_page_text(html_path)
            raw_parts.append(txt[:1500])
    if PROD_FINDINGS.exists():
        pf = json.loads(PROD_FINDINGS.read_text(encoding="utf-8"))
        for page in pf.get("pages", []):
            if page["page"] in ("赛事详情", "Predict More Matches", "联赛页", "球队页", "球员页", "直播页", "资讯页", "个人中心"):
                raw_parts.append(f"\n## 生产深度体验（{page['page']}）")
                raw_parts.append("\n".join(page.get("findings", page.get("modules", []))))
    return {"modules": modules, "overall_assessment": f"{export_label}/{module_name} 全量功能点"}, "\n".join(raw_parts)


async def run(module_path: str, pick: str, out: Path) -> int:
    from app.services import ai_service
    extraction, content = build_extraction(module_path, pick)
    print(f"[gen] 模块 {module_path}：{len(extraction['modules'])} 页 / {sum(len(m['function_points']) for m in extraction['modules'])} 功能点", flush=True)
    result = await ai_service.generate_test_cases(content, file_type="", source_ref=f"batch-125/{module_path}", extraction=extraction)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    cases = result.get("functional_cases") or result.get("cases") or []
    print(f"[gen] 生成 {len(cases)} 条基础用例 → {out}", flush=True)
    if result.get("_warnings"):
        print("[warn]", result["_warnings"], flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True, help="模块路径，如 运营后台/赛事预测 或 用户端/赛事详情")
    ap.add_argument("--pick", default="", help="页面名/功能点筛选")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or (OUT_DIR / (args.module.replace("/", "-") + ".json"))
    return asyncio.run(run(args.module, args.pick, out))


if __name__ == "__main__":
    sys.exit(main())
