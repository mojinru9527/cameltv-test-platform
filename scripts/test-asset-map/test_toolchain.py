# -*- coding: utf-8 -*-
"""工具链守卫：页面源适配器 / 合并 / 门禁。

用合成数据验证行为，避免依赖真实环境：
- scan-mp 能从 app.json 解析主包+分包
- parse-prd 过滤页脚噪声
- merge 标注来源并产出 PRD-only 缺口
- gate 在断言通过率不足时返回非 0
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(HERE))


def test_scan_mp_pages(tmp_path: Path):
    app = {
        "pages": ["pages/home/home", "pages/my/my"],
        "subPackages": [{"root": "pages-sub/order/", "pages": ["order-list", "order-detail"]}],
    }
    (tmp_path / "app.json").write_text(json.dumps(app), encoding="utf-8")
    out = tmp_path / "mp.json"
    r = run(HERE / "adapters.py", "scan-mp", "--app-json", tmp_path / "app.json", "--out", out)
    assert r.returncode == 0, r.stderr
    pages = json.loads(out.read_text(encoding="utf-8"))
    assert len(pages) == 4
    assert all(p["source"] == "scan-mp" for p in pages)
    assert {p["group"] for p in pages} == {"主包", "pages-sub/order"}


def test_parse_prd_filters_noise(tmp_path: Path):
    prd = tmp_path / "prd.txt"
    prd.write_text(
        "第 1 页 共 9 页\n"
        "3.1 订单详情页面\n"
        "3.2 组件列表页\n"
        "该接口返回 code=200，字段 name 必填。\n"
        "用于说明的一段很长的描述文字，包含了很多内容，不应该被当成页面。\n",
        encoding="utf-8")
    out = tmp_path / "prd.json"
    r = run(HERE / "adapters.py", "parse-prd", "--input", prd, "--out", out)
    assert r.returncode == 0, r.stderr
    pages = json.loads(out.read_text(encoding="utf-8"))
    names = [p["name"] for p in pages]
    assert all("共 9 页" not in n for n in names)
    assert any("订单详情" in n for n in names)


def test_merge_reports_prd_only_gap(tmp_path: Path):
    impl = [{"platform": "web", "page_id": "W1", "group": "g", "name": "订单详情",
             "path": "/order/detail", "component": "", "page_kind": "detail", "source": "crawl-web"}]
    prd = [{"platform": "prd", "page_id": "P1", "group": "PRD", "name": "订单详情",
            "path": "", "component": "", "page_kind": "detail", "source": "parse-prd"},
           {"platform": "prd", "page_id": "P2", "group": "PRD", "name": "会员权益中心",
            "path": "", "component": "", "page_kind": "list", "source": "parse-prd"}]
    (tmp_path / "impl.json").write_text(json.dumps(impl, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "prd.json").write_text(json.dumps(prd, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "merged.json"
    r = run(HERE / "adapters.py", "merge", "--source", f"crawl={tmp_path/'impl.json'}",
            "--source", f"prd={tmp_path/'prd.json'}", "--out", out)
    assert r.returncode == 0, r.stderr
    merged = json.loads(out.read_text(encoding="utf-8"))
    assert len(merged) == 2
    gaps = json.loads((tmp_path / "merged.gaps.json").read_text(encoding="utf-8"))
    assert [g["name"] for g in gaps] == ["会员权益中心"]


def _write_assertions(path: Path, statuses: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rule_id", "page", "assertion", "status", "metric", "evidence"])
        w.writeheader()
        for i, s in enumerate(statuses):
            w.writerow({"rule_id": "R07", "page": f"p{i}", "assertion": "A07",
                        "status": s, "metric": "", "evidence": ""})


def test_gate_blocks_on_low_pass_rate(tmp_path: Path):
    summary = {"project": "t", "pages": 10, "pages_with_path": 10, "endpoints": 100,
               "unassigned_endpoints": []}
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    _write_assertions(tmp_path / "a.csv", ["PASS", "FAIL", "FAIL", "FAIL"])
    r = run(HERE / "gate.py", "--summary", tmp_path / "summary.json",
            "--assertions", tmp_path / "a.csv", "--out", tmp_path / "g.json")
    assert r.returncode == 1
    report = json.loads((tmp_path / "g.json").read_text(encoding="utf-8"))
    assert report["pass"] is False


def test_gate_passes_when_all_ok(tmp_path: Path):
    summary = {"project": "t", "pages": 10, "pages_with_path": 10, "endpoints": 100,
               "unassigned_endpoints": ["GET /x"]}
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    _write_assertions(tmp_path / "a.csv", ["PASS"] * 10)
    r = run(HERE / "gate.py", "--summary", tmp_path / "summary.json",
            "--assertions", tmp_path / "a.csv", "--out", tmp_path / "g.json")
    assert r.returncode == 0


def test_suggest_domains_covers_all_paths(tmp_path: Path):
    eps = ([{"method": "GET", "path": f"/system/component/item{i}"} for i in range(10)]
           + [{"method": "GET", "path": f"/client/mall/cart{i}"} for i in range(10)]
           + [{"method": "POST", "path": "/auth/login"}, {"method": "GET", "path": "/auth/code"}])
    src = tmp_path / "eps.json"
    src.write_text(json.dumps(eps), encoding="utf-8")
    out = tmp_path / "suggest.json"
    r = run(HERE / "suggest_domains.py", "--endpoints", src, "--min-size", "3", "--out", out)
    assert r.returncode == 0, r.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["candidate_domains"] >= 2
    covered = sum(c["api_count"] for c in report["candidates"])
    assert covered <= report["endpoints"]
    assert report["coverage_by_prefix"].split("/")[0].isdigit()


def test_gen_chain_specs_marks_ready_and_skeleton(tmp_path: Path):
    graph = {"chains": {
        "订单-C端": {"domain": "订单-C端", "api_count": 3, "stages": ["list"],
                     "nodes": [{"stage": "list", "apis": ["GET /client/mall/orders"]}]},
        "某新域": {"domain": "某新域", "api_count": 2, "stages": ["detail"],
                    "nodes": [{"stage": "detail", "apis": ["GET /system/foo/detail"]}]},
    }}
    g = tmp_path / "graph.json"
    g.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "chains"
    r = run(HERE / "gen_chain_specs.py", "--graph", g, "--out-dir", out, "--project", "t")
    assert r.returncode == 0, r.stderr
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    statuses = {m["domain"]: m["status"] for m in manifest["chains"]}
    assert statuses["订单-C端"] == "ready"
    assert statuses["某新域"] == "skeleton"
    assert (out / "CHAIN-ORDER-C-READONLY.json").exists()
