"""Bind an A3 workflow plan to a concrete Test environment (M3 gate adapter).

A3 输出的是与业务/环境无关的计划；执行前必须做三件确定性绑定：
1. 相对 URL -> Test HTTP / UI base URL；
2. 非 Runtime action 名 -> Runtime action 名（如 wait_for -> wait_visible）；
3. 给 click 前补 wait_visible，避免 SPA 首屏未渲染时空点；
   可选 selector-map 修正文本选择器为稳定属性选择器。

这不是人工改图：输入输出都是机器可复核 JSON，绑定规则以参数固化。

Usage:
  python scripts/qa/aiqe_a3_bind_plan.py \
    --plan a3_plan.json --http-base http://aiqe-test-nginx:80 \
    --ui-base http://127.0.0.1:28080 --timeout-ms 45000 \
    --selector-map '{"text=忘记密码": "a[href=\"/forgot-password\"]"}' \
    --output bound_graph.json
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def _bind_url(url: str, base: str) -> str:
    if not url:
        return url
    if url.startswith("/"):
        return base.rstrip("/") + url
    return url


def bind_plan(
    plan: dict[str, Any],
    *,
    http_base: str,
    ui_base: str,
    timeout_ms: int,
    selector_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    workflow = copy.deepcopy(plan.get("workflow") or plan)
    selector_map = selector_map or {}
    for node in workflow.get("nodes") or []:
        driver = str(node.get("driver") or "")
        payload = node.setdefault("input", {})
        if driver == "http":
            payload["url"] = _bind_url(str(payload.get("url") or ""), http_base)
        if driver == "playwright":
            payload["url"] = _bind_url(str(payload.get("url") or ""), ui_base)
            payload["timeout_ms"] = timeout_ms
            actions = []
            for raw in payload.get("actions") or []:
                action = copy.deepcopy(raw)
                if action.get("type") == "wait_for":
                    action["type"] = "wait_visible"
                if action.get("selector") in selector_map:
                    action["selector"] = selector_map[action["selector"]]
                action["timeout_ms"] = int(action.get("timeout_ms") or timeout_ms)
                if action.get("type") == "click" and not any(
                    item.get("type") in {"wait_visible", "assert_visible"}
                    and item.get("selector") == action.get("selector")
                    for item in actions
                ):
                    actions.append(
                        {
                            "type": "wait_visible",
                            "selector": action.get("selector"),
                            "timeout_ms": timeout_ms,
                        }
                    )
                actions.append(action)
            payload["actions"] = actions
        for assertion in node.get("assertions") or []:
            if assertion.get("selector") in selector_map:
                assertion["selector"] = selector_map[assertion["selector"]]
    workflow.setdefault(
        "run_policy", {"max_parallel_nodes": 3, "fail_fast": False}
    )
    workflow["run_policy"]["max_parallel_nodes"] = int(
        workflow["run_policy"].get("max_parallel_nodes") or 3
    )
    return workflow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--http-base", required=True)
    parser.add_argument("--ui-base", required=True)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--selector-map", default="{}")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if "plan" in plan and isinstance(plan["plan"], dict):
        plan = plan["plan"]
    workflow = bind_plan(
        plan,
        http_base=args.http_base,
        ui_base=args.ui_base,
        timeout_ms=args.timeout_ms,
        selector_map=json.loads(args.selector_map),
    )
    Path(args.output).write_text(
        json.dumps({"graph": workflow}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": args.output, "nodes": len(workflow["nodes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
