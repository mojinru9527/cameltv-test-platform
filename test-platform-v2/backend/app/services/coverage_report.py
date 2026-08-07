"""C116-3 — 覆盖缺口报告（C103-6 落地）。

输入：确认的功能点提取（modules→function_points）与生成结果（functional_cases），
输出：模块×功能点 覆盖矩阵 + 缺口清单（覆盖缺口报告）。
"""
from __future__ import annotations

import json


def _module_match(case: dict, module_name: str) -> bool:
    cmod = str(case.get("module") or "")
    ctitle = str(case.get("title") or "")
    return module_name in cmod or module_name in ctitle or cmod in module_name


def build_coverage_report(extraction: dict | None, generated: dict | None) -> dict:
    modules = (extraction or {}).get("modules") or []
    cases = (generated or {}).get("functional_cases") or []
    matrix: list[dict] = []
    gaps: list[dict] = []
    total_fp = 0
    for mod in modules:
        name = str(mod.get("name") or "")
        fps = mod.get("function_points") or []
        mod_cases = [c for c in cases if _module_match(c, name)]
        for fp in fps:
            fp_name = str(fp.get("name") or fp.get("id") or "")
            total_fp += 1
            covered = any(
                fp_name in str(c.get("title") or "") + str(c.get("module") or "")
                for c in mod_cases
            )
            matrix.append({
                "module": name, "function_point": fp_name,
                "covered": covered, "case_count": len(mod_cases),
            })
            if not covered:
                gaps.append({"module": name, "function_point": fp_name})
    return {
        "matrix": matrix,
        "gaps": gaps,
        "gap_count": len(gaps),
        "total_fp": total_fp,
        "covered_fp": total_fp - len(gaps),
        "coverage_rate": round((total_fp - len(gaps)) / total_fp, 4) if total_fp else 0.0,
    }


def parse_extraction(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None