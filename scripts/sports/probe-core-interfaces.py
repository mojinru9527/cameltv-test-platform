"""体育平台承接 — 生产核心接口真实样本回填探测（Batch 110，C103-4/5）。

对 SSR 页面未产生 XHR 的核心功能接口，按 Test5 契约（camel-service）确认参数，
用生产页面真实值（matchId/competitionId/语言/分页）回填请求参数，调用生产 API
记录真实请求与响应（响应作为后续接口用例断言基线）。全部为只读 GET/POST 查询。

运行: <venv-python> scripts/sports/probe-core-interfaces.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "xhr-samples"
API = "https://api.cameltv.live"

MATCH_ID = "965mkyhkvjklr1g"           # 生产赛事详情页真实 matchId（Jagiellonia vs Rangers）
UEFA_ID = "56ypq3nh0xmd7oj"            # 生产 get_competition_by_name 返回
WORLDCUP_ID = "kp3glrw7hwqdyjv"        # 生产 get_competition_by_name(FIFA World Cup) 返回
REPLAY_ID = "107123464706493798"       # 生产回放列表真实记录 id


def _load_news_id() -> str:
    """从已捕获的 list_visible 真实响应中提取一条真实资讯 id。"""
    srcs = [
        EVIDENCE_DIR.parent / "production-walkthrough-v2" / "xhr-samples.json",
        EVIDENCE_DIR / "xhr-samples-merged.json",
        EVIDENCE_DIR / "xhr-samples-interactions.json",
    ]
    for f in srcs:
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for s in data.get("samples", []):
            if s.get("path", "").endswith("/ee/news/list_visible") and s.get("response"):
                try:
                    body = json.loads(s["response"])
                    records = body.get("data", {}).get("records") or body.get("data", {}).get("data") or []
                    if records:
                        return str(records[0].get("id", ""))
                except Exception:
                    continue
    return "1"


TARGETS = [
    {"name": "首页-热门赛事", "method": "GET", "path": "/camel-service/ee/sports_live/hot_match", "query": {"page": 1, "size": 10}},
    {"name": "首页-热门球队", "method": "GET", "path": "/camel-service/ee/sports_live/hot_team", "query": {}},
    {"name": "首页-热门分组", "method": "GET", "path": "/camel-service/ee/sports_live/hot_group_match", "query": {}},
    {"name": "赛事详情-赛前分析", "method": "GET", "path": "/camel-service/ee/sports_live/football/match/analysis", "query": {"matchId": MATCH_ID}},
    {"name": "赛事详情-阵容", "method": "GET", "path": "/camel-service/ee/sports_live/football/match/lineup", "query": {"matchId": MATCH_ID}},
    {"name": "赛事详情-球队统计", "method": "GET", "path": "/camel-service/ee/sports_live/football/match/team_stats/list", "query": {"matchId": MATCH_ID}},
    {"name": "赛事详情-时间线", "method": "GET", "path": "/camel-service/ee/sports_live/football/match/time", "query": {"matchId": MATCH_ID}},
    {"name": "回放-列表", "method": "GET", "path": "/camel-service/ee/replay/list", "query": {"page": 1, "size": 10}},
    {"name": "回放-详情", "method": "GET", "path": "/camel-service/ee/replay/get", "query": {"id": REPLAY_ID}},
    {"name": "世界杯-赛程", "method": "GET", "path": "/camel-service/ee/fifa/football/season/match", "query": {"competitionId": WORLDCUP_ID, "page": 1, "size": 10}},
    {"name": "资讯-分类", "method": "GET", "path": "/camel-service/ee/news_kind/list", "query": {}},
    {"name": "资讯-详情(可见)", "method": "GET", "path": "/camel-service/ee/news/get_visible", "query": {"id": None}},
    {"name": "资讯-详情(全文)", "method": "GET", "path": "/camel-service/ee/news/get", "query": {"id": None}},
    {"name": "联赛-详情", "method": "GET", "path": "/camel-service/ee/sports_live/get_competition_by_name", "query": {"name": "UEFA Europa League"}},
    {"name": "球队-详情", "method": "GET", "path": "/camel-service/ee/sports_live/get_team_by_name", "query": {"name": "Petro Atletico de Luanda"}},
    {"name": "联赛-赛程", "method": "GET", "path": "/camel-service/ee/sports_live/football/season/match", "query": {"competitionId": UEFA_ID, "page": 1, "size": 10}},
    {"name": "联赛-积分榜", "method": "GET", "path": "/camel-service/ee/sports_live/football/season/recent/table/detail", "query": {"competitionId": UEFA_ID}},
    {"name": "赔率-汇总", "method": "GET", "path": "/camel-service/ee/forecast/queryOddsSummaryByMatchId", "query": {"matchId": MATCH_ID}},
    {"name": "资讯-相关推荐", "method": "POST", "path": "/camel-service/ee/news/related", "query": {"id": None}},
]


def main() -> int:
    news_id = _load_news_id()
    for t in TARGETS:
        if "id" in t["query"] and t["query"]["id"] is None:
            t["query"]["id"] = news_id

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    samples = []
    with httpx.Client(base_url=API, timeout=40, headers={"Accept": "application/json"}) as client:
        for t in TARGETS:
            url = t["path"]
            try:
                if t["method"] == "GET":
                    r = client.get(url, params=t["query"])
                else:
                    r = client.post(url, params=t["query"])
                body = r.text
                ok = r.status_code == 200
                samples.append({
                    "module": t["name"],
                    "method": t["method"],
                    "url": API + url,
                    "host": "api.cameltv.live",
                    "path": url + ("?" + "&".join(f"{k}={v}" for k, v in t["query"].items()) if t["query"] else ""),
                    "post_data": "" if t["method"] == "GET" else json.dumps({}, ensure_ascii=False),
                    "status": r.status_code,
                    "response": body[:250000],
                    "source": "生产回填探测（契约参数 + 生产真实值）",
                    "ts": int(time.time() * 1000),
                })
                print(f"[{'OK ' if ok else 'ERR'}] {t['name']} {r.status_code} len={len(body)}", flush=True)
            except Exception as exc:
                samples.append({
                    "module": t["name"], "method": t["method"], "url": API + url,
                    "host": "api.cameltv.live", "path": url, "post_data": "",
                    "status": 0, "response": f"error: {exc}", "source": "生产回填探测（失败）", "ts": int(time.time() * 1000),
                })
                print(f"[ERR] {t['name']}: {exc}", flush=True)

    out = EVIDENCE_DIR / "xhr-samples-probed.json"
    out.write_text(json.dumps({"base": API, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "samples": samples}, ensure_ascii=False, indent=2), encoding="utf-8")
    ok_count = sum(1 for s in samples if s["status"] == 200)
    print(f"[done] probed={len(samples)} ok={ok_count} saved={out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
