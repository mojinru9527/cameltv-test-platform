# -*- coding: utf-8 -*-
"""体育模块用例合并（Batch 125 / Slice 3 收口）。

每个模块 = 基座基础用例（新生成，两 skill 基座）+ 深度用例（Batch 122 SP- 手工深度层）。

输出：test-platform-v2/work-logs/evidence/batch-125/module-cases-consolidated.json
结构：{ modules: [{ module, base_count, deep_count, total_count, base: [...], deep: [...] }], summary }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "base-cases"
DEEP_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-122" / "cases"
OUT = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "module-cases-consolidated.json"


def load_base(module_path: str) -> list[dict]:
    fname = module_path.replace("/", "-") + ".json"
    fp = BASE_DIR / fname
    if not fp.exists():
        return []
    data = json.loads(fp.read_text(encoding="utf-8"))
    return data.get("functional_cases") or data.get("cases") or []


def load_deep() -> dict[str, list[dict]]:
    """按 module 聚合 Batch 122 深度用例。"""
    by_module: dict[str, list[dict]] = {}
    for fp in sorted(DEEP_DIR.rglob("*.json")):
        try:
            cases = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        for c in cases:
            mod = c.get("module") or ""
            by_module.setdefault(mod, []).append(c)
    return by_module


def norm_module_key(s: str) -> str:
    return s.replace("/", " ").replace("-", " ").lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    inv = json.loads((REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "sports-feature-inventory.json").read_text(encoding="utf-8"))
    modules: list[str] = []
    for label, exp in inv["exports"].items():
        for m in exp["modules"]:
            modules.append(f"{label}/{m['name']}")

    deep_map = load_deep()
    all_deep_flat = [c for cs in deep_map.values() for c in cs]
    # 深度用例按模块名模糊匹配（如 用户端/赛事详情 ↔ 赛事详情/预测Pick、运营后台/赛事预测 ↔ 运营后台/赛事预测/奖励发放记录）
    matched_ids: set[str] = set()
    result_modules = []
    total_base = total_deep = 0
    for mod in modules:
        base = load_base(mod)
        key = norm_module_key(mod)
        tail = key.split()[-1]
        matched = []
        for c in all_deep_flat:
            ck = norm_module_key(c.get("module", ""))
            if c.get("case_id") in matched_ids:
                continue
            if tail in ck or ck in key:
                matched.append(c)
                matched_ids.add(c.get("case_id"))
        deep_list = list({c.get("case_id"): c for c in matched}.values())
        result_modules.append({
            "module": mod,
            "base_count": len(base),
            "deep_count": len(deep_list),
            "total_count": len(base) + len(deep_list),
            "base": base,
            "deep": deep_list,
        })
        total_base += len(base)
        total_deep += len(deep_list)
    # 未匹配的深度用例（如 接口/konfi/跨模块）按自身模块追加，确保全部包含
    unmatched = [c for c in all_deep_flat if c.get("case_id") not in matched_ids]
    by_mod: dict[str, list[dict]] = {}
    for c in unmatched:
        by_mod.setdefault(c.get("module") or "体育-其他", []).append(c)
    for mod_name, deep_list in sorted(by_mod.items()):
        result_modules.append({
            "module": mod_name,
            "base_count": 0,
            "deep_count": len(deep_list),
            "total_count": len(deep_list),
            "base": [],
            "deep": deep_list,
        })
        total_deep += len(deep_list)

    summary = {"module_count": len(modules), "total_base": total_base, "total_deep": total_deep, "total": total_base + total_deep}
    out_data = {"summary": summary, "modules": result_modules}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"汇总：{summary}")
    print(f"输出 -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
