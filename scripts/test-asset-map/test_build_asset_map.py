# -*- coding: utf-8 -*-
"""适配器与引擎的可移植性守卫。

断言三件事：
1. 两个真实项目适配器都能被同一引擎跑通（跨项目复用）；
2. 适配器符合 project-adapter.schema.json；
3. 引擎输出满足标准里的准出线（接口分配率 ≥95%、页面清单非空、矩阵可复算）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
jsonschema = pytest.importorskip("jsonschema")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ADAPTER_DIR = REPO / "docs" / "standards" / "project-adapters"
SCHEMA = ADAPTER_DIR / "project-adapter.schema.json"
ENGINE = HERE / "build_asset_map.py"

ADAPTERS = ["futurewayu.adapter.yaml", "cameltv-sports.adapter.yaml"]


def _run(adapter: Path) -> dict:
    out = adapter.parent / "out" / adapter.stem.replace(".adapter", "")
    subprocess.run([sys.executable, str(ENGINE), str(adapter)], check=True,
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=str(REPO))
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ADAPTERS)
def test_adapter_matches_schema(name: str):
    adapter = yaml.safe_load((ADAPTER_DIR / name).read_text(encoding="utf-8"))
    jsonschema.validate(adapter, json.loads(SCHEMA.read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", ADAPTERS)
def test_engine_reusable_across_projects(name: str):
    summary = _run(ADAPTER_DIR / name)
    assert summary["pages"] > 0
    assert summary["rules"] == 24
    assert summary["matrix_cells"] == summary["pages"] * summary["rules"]
    assert summary["applicable_cells"] > 0
    # 准出线：未归类接口 ≤5%
    unassigned_ratio = len(summary["unassigned_endpoints"]) / max(1, summary["endpoints"])
    assert unassigned_ratio <= 0.05, f"{name} 未归类接口过多: {unassigned_ratio:.1%}"
    assert summary["unique_paths"] <= summary["endpoints"]


def test_rules_library_is_project_agnostic():
    rules = json.loads((REPO / ".claude" / "skills" / "interaction-case-augmenter" /
                        "references" / "interaction-rules.json").read_text(encoding="utf-8"))["rules"]
    assert len(rules) >= 20
    ids = [r["rule_id"] for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        assert r["assertion"].startswith("A"), r["rule_id"]
        assert r["invariant"] and r["page_kinds"]
    blob = json.dumps(rules, ensure_ascii=False)
    # 准则库不得混入具体项目业务词，否则不可复用
    for forbidden in ("未来娃屿", "CamelTv", "球鞋", "娃娃"):
        assert forbidden not in blob, f"准则库混入了项目词: {forbidden}"
