"""Regenerate tests/fixtures/route_inventory.json from the live OpenAPI.

The fixture is the route+method baseline for ``test_route_paths_match_baseline``.
Running this after intentionally adding/removing routes keeps the baseline in sync
(route-split P2-10 acceptance). Run from the backend dir.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.main import app

spec = app.openapi()
routes = []
for path, ops in spec["paths"].items():
    for method in ops:
        if method in ("head", "options", "parameters"):
            continue
        routes.append({"path": path, "method": method.upper()})
routes.sort(key=lambda r: (r["path"], r["method"]))

out = {"count": len(routes), "routes": routes}
dest = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "route_inventory.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"regenerated {dest} with {len(routes)} routes")
