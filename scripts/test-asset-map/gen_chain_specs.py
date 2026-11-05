#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按接口依赖图生成域内链规格（P0 三域为可执行规格，其余为骨架）。

输入：interface-chain-graph.json
输出：chains/<project>/CHAIN-<domain>.json + manifest.json

约定：
- 只把只读阶段（list/detail）放进默认步骤，写阶段（create/publish/transact/delete）
  一律标记 skeleton + todo，避免脚本在生产环境误写。
- auth 由路径推断：/client/** → client；/system/**、/monitor/** → admin。
- P0 域（资产-组件 / 订单-C端 / 有赞-交易）使用带夹具与断言的完整规格。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

READONLY_STAGES = {"list", "detail"}

P0_TEMPLATES = {
    "资产-组件": {
        "chain_id": "CHAIN-ASSET-COMPONENT-READONLY",
        "name": "资产-组件域内链：列表→详情→分类/系列字典→C 端商品可见",
        "fixtures": [
            {"id": "f1", "name": "后台取一个组件", "method": "GET",
             "path": "/system/component/list?pageNum=1&pageSize=1", "auth": "admin",
             "expect": {"code": 200}, "extract": {"cid": "rows[0].id"}},
        ],
        "entry_gate": ["f1"],
        "steps": [
            {"no": 1, "name": "组件详情", "method": "GET", "path": "/system/component/{cid}",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 2, "name": "组件分类树", "method": "GET", "path": "/system/componentCategory/getTreeList",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 3, "name": "系列下拉", "method": "GET", "path": "/system/componentSeries/optionselect",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 4, "name": "C 端商品详情可见", "method": "GET", "path": "/client/mall/products/{cid}",
             "auth": "client", "expect": {"code": 200}, "present": True,
             "absent_fields": ["openid", "sessionKey"]},
        ],
        "cleanup": [],
        "priority": "P0",
    },
    "订单-C端": {
        "chain_id": "CHAIN-ORDER-C-READONLY",
        "name": "订单-C 端域内链：订单列表→详情→可退金额→退款记录→购物车",
        "fixtures": [
            {"id": "f1", "name": "C 端最近订单", "method": "GET",
             "path": "/client/mall/orders?pageNum=1&pageSize=5", "auth": "client",
             "expect": {"code": 200}, "extract": {"bno": "data[0].businessNo"}},
        ],
        "entry_gate": ["f1"],
        "steps": [
            {"no": 1, "name": "订单详情", "method": "GET", "path": "/client/mall/orders/{bno}",
             "auth": "client", "expect": {"code": 200}, "present": True,
             "absent_fields": ["openid", "sessionKey"]},
            {"no": 2, "name": "可退金额", "method": "GET", "path": "/client/mall/orders/{bno}/refundable",
             "auth": "client", "expect": {"code_in": [200, 4100]},
             "note": "4100=业务拒绝（不可退），需业务确认文案"},
            {"no": 3, "name": "退款记录", "method": "GET", "path": "/client/mall/orders/{bno}/refunds",
             "auth": "client", "expect": {"code": 200}},
            {"no": 4, "name": "购物车", "method": "GET", "path": "/client/mall/cart",
             "auth": "client", "expect": {"code": 200}, "present": True},
        ],
        "cleanup": [],
        "priority": "P0",
    },
    "有赞-交易": {
        "chain_id": "CHAIN-YOUZAN-TRADE-READONLY",
        "name": "有赞-交易域内链：门店支付配置→退款记录→退款可退金额→商品条码告警",
        "fixtures": [
            {"id": "f1", "name": "有赞店铺列表", "method": "GET", "path": "/system/youzan/store/list",
             "auth": "admin", "expect": {"code": 200}, "extract": {"sid": "rows[0].id"}},
        ],
        "entry_gate": ["f1"],
        "steps": [
            {"no": 1, "name": "店铺详情", "method": "GET", "path": "/system/youzan/store/{sid}",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 2, "name": "自提点收款配置", "method": "GET", "path": "/system/youzan/store/{sid}/point-payments",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 3, "name": "商品条码告警列表", "method": "GET", "path": "/system/youzan/goods/alert/list?pageNum=1&pageSize=5",
             "auth": "admin", "expect": {"code": 200}},
            {"no": 4, "name": "身份刷新接口鉴权（无 body 应为业务错误而非 500）",
             "method": "POST", "path": "/system/youzan/identity/refresh", "auth": "admin",
             "body": {}, "expect": {"code_in": [400, 200]}},
        ],
        "cleanup": [],
        "priority": "P0",
    },
}


def slugify(domain: str) -> str:
    table = {"资产-组件": "asset-component", "订单-C端": "order-client", "有赞-交易": "youzan-trade"}
    if domain in table:
        return table[domain]
    s = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", domain)
    return "dom-" + re.sub(r"-+", "-", s).strip("-")


def auth_of(path: str) -> str:
    return "client" if path.startswith("/client") else "admin"


def build_skeleton(domain: str, chain: dict) -> dict:
    steps = []
    no = 0
    for node in chain["nodes"]:
        if node["stage"] not in READONLY_STAGES:
            continue
        for api in node["apis"][:3]:
            method, path = api.split(" ", 1)
            if method != "GET" or "{" in path:
                continue
            no += 1
            steps.append({"no": no, "name": f'{node["stage"]}:{path}', "method": "GET", "path": path,
                          "auth": auth_of(path), "expect": {"code": 200}})
    return {
        "chain_id": f"CHAIN-{slugify(domain).upper()}",
        "name": f"{domain} 域内链（骨架，只读步骤已生成）",
        "priority": "P2",
        "status": "skeleton",
        "fixtures": [],
        "entry_gate": [],
        "steps": steps[:8],
        "cleanup": [],
        "todo": [
            "补充前置夹具（造数链：上游实体 → 本域）",
            "补充写阶段步骤与状态/数据/幂等断言",
            "补充失败注入（并发/重复/乱序）与清理契约",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--project", default="futurewayu")
    args = ap.parse_args()

    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = []
    for domain, chain in graph["chains"].items():
        if domain in P0_TEMPLATES:
            spec = dict(P0_TEMPLATES[domain])
            spec["status"] = "ready"
            spec["domain"] = domain
            spec["api_count"] = chain["api_count"]
        else:
            spec = build_skeleton(domain, chain)
            spec["domain"] = domain
            spec["api_count"] = chain["api_count"]
        path = out / f"{spec['chain_id']}.json"
        path.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest.append({"chain_id": spec["chain_id"], "domain": domain,
                         "priority": spec.get("priority"), "status": spec.get("status"),
                         "api_count": chain["api_count"], "steps": len(spec.get("steps") or []),
                         "file": path.name})

    manifest.sort(key=lambda x: ({"P0": 0, "P1": 1, "P2": 2}.get(x["priority"], 3), -x["api_count"]))
    (out / "manifest.json").write_text(json.dumps({"project": args.project, "chains": manifest},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    ready = [m for m in manifest if m["status"] == "ready"]
    skel = [m for m in manifest if m["status"] == "skeleton"]
    print(f"chains={len(manifest)} ready={len(ready)} skeleton={len(skel)}")
    print("ready:", [m["chain_id"] for m in ready])
    print("top skeleton:", [m["chain_id"] for m in skel[:5]])
    print("->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
