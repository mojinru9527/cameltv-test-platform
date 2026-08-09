# -*- coding: utf-8 -*-
"""体育平台全模块基座用例批量生成（Batch 125 / Slice 3 全量）。

遍历运营后台 17 模块 + 用户端 21 模块（共 38 模块 / 183 页），
每模块走 run_base_case_generation 的 extraction 分块生成链路（两 skill 基座）。

特性：
- 断点续跑：已生成且非空的模块跳过（--force 重跑）
- 失败重试：单模块失败重试 1 次
- 汇总：输出 base-cases-summary.json（每模块页数/功能点/用例数/失败）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[3]
INVENTORY = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "sports-feature-inventory.json"
OUT_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "base-cases"

from run_base_case_generation import build_extraction  # noqa: E402


def module_list() -> list[str]:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    out = []
    for label, exp in inv["exports"].items():
        for m in exp["modules"]:
            out.append(f"{label}/{m['name']}")
    return out


def safe_name(module_path: str) -> str:
    return module_path.replace("/", "-")


async def gen_module(module_path: str, force: bool) -> dict:
    from app.services import ai_service
    out = OUT_DIR / (safe_name(module_path) + ".json")
    if out.exists() and not force:
        try:
            exist = json.loads(out.read_text(encoding="utf-8"))
            n = len(exist.get("functional_cases") or [])
            if n > 0:
                return {"module": module_path, "status": "skipped", "cases": n}
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            print(
                f"[run-all] 缓存 {out} 无效，将重新生成：{exc}",
                file=sys.stderr,
                flush=True,
            )
    try:
        extraction, content = build_extraction(module_path)
        fp_count = sum(len(m["function_points"]) for m in extraction["modules"])
        result = await ai_service.generate_test_cases(
            content, file_type="", source_ref=f"batch-125/{module_path}", extraction=extraction
        )
        cases = result.get("functional_cases") or []
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"module": module_path, "status": "ok", "pages": len(extraction["modules"]), "fps": fp_count, "cases": len(cases), "warnings": result.get("_warnings", [])}
    except Exception as exc:  # noqa: BLE001
        return {"module": module_path, "status": "failed", "error": str(exc)[:200]}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", nargs="*", default=None, help="指定模块（默认全部 38 个）")
    ap.add_argument("--force", action="store_true", help="重跑已生成模块")
    ap.add_argument("--max-modules", type=int, default=0, help="最多跑 N 个模块（0=全部）")
    args = ap.parse_args()

    modules = args.modules or module_list()
    if args.max_modules:
        modules = modules[: args.max_modules]

    print(f"[run-all] 共 {len(modules)} 个模块", flush=True)
    summary: list[dict] = []
    ok = fail = 0
    total_cases = 0
    for i, m in enumerate(modules, start=1):
        print(f"[run-all] [{i}/{len(modules)}] {m}", flush=True)
        res = await gen_module(m, args.force)
        # 失败重试一次
        if res["status"] == "failed":
            print(f"[run-all] 重试 {m} ...", flush=True)
            res = await gen_module(m, True)
        summary.append(res)
        if res["status"] in ("ok", "skipped"):
            ok += 1
            total_cases += res.get("cases", 0)
        else:
            fail += 1
        print(f"[run-all] -> {res['status']} cases={res.get('cases', 0)}", flush=True)

    sum_out = OUT_DIR / "base-cases-summary.json"
    sum_out.write_text(
        json.dumps({"total_modules": len(modules), "ok": ok, "failed": fail, "total_cases": total_cases, "modules": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"[run-all] 完成：ok={ok} failed={fail} total_cases={total_cases} → {sum_out}", flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
