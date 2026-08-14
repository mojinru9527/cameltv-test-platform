"""Batch 181（FIX-173-P2-10）— 路由路径集基线守卫。

用途：路由文件按域拆分后，URL 路径与 HTTP 方法必须零变化。
基线 `tests/fixtures/route_inventory.json` 在拆分前从 OpenAPI 生成（420 条），
任何拆分导致的路径漂移（增/删/改）都会使本测试失败。
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "route_inventory.json"


def _live_routes() -> set[tuple[str, str]]:
    from app.main import app

    spec = app.openapi()
    out = set()
    for path, ops in spec["paths"].items():
        for method in ops:
            if method in ("head", "options", "parameters"):
                continue
            out.add((path, method.upper()))
    return out


def test_route_paths_match_baseline():
    """拆分前后路径+方法集合必须与基线完全一致（P2-10 验收）。"""
    baseline = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = {(r["path"], r["method"]) for r in baseline["routes"]}
    live = _live_routes()

    assert live == expected, (
        f"路由集合漂移: 新增 {sorted(live - expected)[:10]} / 丢失 {sorted(expected - live)[:10]}"
    )
    assert len(live) == baseline["count"]
