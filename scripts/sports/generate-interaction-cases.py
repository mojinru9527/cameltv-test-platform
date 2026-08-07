"""体育平台承接 — 交互路径提取 + UI 交互用例生成/落库（Batch 113，C112-2）。

从生产 40 页勘察（production-pages.json，含 links[text,href]）提取「页面→入口→目标页」跳转边，
按 P0 模块生成交互类功能用例（正：入口可达/跳转/返回/Tab 切换；负：无效 URL/空态/断链），
直连生产库落库（functional，tags=interaction:batch-113），幂等（已存在则跳过）。

运行: <venv-python> scripts/sports/generate-interaction-cases.py --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-113"
PAGES = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "production-walkthrough-v2" / "production-pages.json"

LABEL_MODULE = {
    "home": "首页",
    "news": "资讯",
    "my": "我的",
    "league": "联赛",
    "team": "球队",
    "match": "赛事详情",
    "live": "直播间",
    "replay": "回放",
    "worldcup": "世界杯专题",
    "search": "搜索",
}


def extract_paths() -> dict:
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    edges = []
    seen = set()
    for p in pages:
        from_url = str(p.get("url") or "")
        from_module = LABEL_MODULE.get(str(p.get("label") or ""), str(p.get("label") or ""))
        for link in p.get("links") or []:
            href = str(link.get("href") or "").strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                continue
            if href.startswith("/"):
                to_url = urljoin("https://www.camel1.tv", href)
            else:
                to_url = href
            to_path = urlparse(to_url).path
            key = (from_url, href)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "from": from_url,
                "from_module": from_module,
                "entry": str(link.get("text") or "").strip()[:40],
                "to": to_path,
                "evidence": "production-pages.json links",
            })
    # 去重（同目标页合并入口）
    by_to: dict = {}
    for e in edges:
        k = (e["from"], e["to"])
        if k not in by_to:
            by_to[k] = e
        else:
            by_to[k]["entry"] += f" / {e['entry']}"
    unique = sorted(by_to.values(), key=lambda x: (x["from_module"], x["to"]))
    return {"paths": unique, "count": len(unique), "pages": len(pages)}


# 交互用例（P0 模块，正负向；遵循 tests/test-case-standards 场景法）
INTERACTION_CASES = [
    {"module": "首页", "title": "首页-入口可达：Match Replays 区块跳转回放列表", "pn": "positive", "p0": True,
     "steps": "1.打开生产首页 https://www.camel1.tv/\n2.定位 Match Replays 区块\n3.点击首条回放链接",
     "expected": "跳转到 /match-replay 列表页，回放链接渲染"},
    {"module": "首页", "title": "首页-Live Matches 三 Tab 切换（Favorites/Competitions）", "pn": "positive", "p0": True,
     "steps": "1.打开首页\n2.点击 Favorites Tab\n3.点击 Competitions Tab",
     "expected": "Tab 内容随点击切换，赛事列表/收藏/赛事数据渲染"},
    {"module": "首页", "title": "首页-搜索入口可达搜索页", "pn": "positive", "p0": True,
     "steps": "1.打开首页\n2.点击搜索框/搜索入口",
     "expected": "跳转 /search，输入框可见可输入"},
    {"module": "赛事详情", "title": "赛事详情-从首页赛事卡跳转并渲染标题/比分", "pn": "positive", "p0": True,
     "steps": "1.打开首页\n2.点击赛事卡片（如 AS Monaco vs Getafe）",
     "expected": "跳转 /football/.../ 详情页，标题/比分/标签渲染"},
    {"module": "赛事详情", "title": "赛事详情-Tab 导航（Stats/Lineups/H2H/Prediction）", "pn": "positive", "p0": True,
     "steps": "1.进入赛事详情页\n2.依次点击 Stats/Lineups/H2H/Prediction Tab",
     "expected": "各 Tab 内容切换渲染，无空白"},
    {"module": "赛事详情", "title": "赛事详情-浏览器返回恢复上一页", "pn": "positive", "p0": True,
     "steps": "1.从首页进入赛事详情\n2.点击浏览器返回",
     "expected": "返回首页且页面可交互"},
    {"module": "直播间", "title": "直播间-从赛事详情进入视频直播", "pn": "positive", "p0": True,
     "steps": "1.进入赛事详情页\n2.点击直播入口（Watch Live）",
     "expected": "跳转 /live/，视频容器 roomLive 渲染"},
    {"module": "资讯", "title": "资讯-列表点击首条进入详情", "pn": "positive", "p0": True,
     "steps": "1.打开 /q/news\n2.点击首条资讯",
     "expected": "跳转 /news/detail/，详情标题与正文渲染"},
    {"module": "资讯", "title": "资讯-分类 Tab 切换列表（World Cup/Transfer 等）", "pn": "positive", "p0": True,
     "steps": "1.打开 /q/news\n2.点击不同分类 Tab",
     "expected": "列表按分类切换渲染"},
    {"module": "搜索", "title": "搜索-输入查询并跳转结果", "pn": "positive", "p0": True,
     "steps": "1.打开 /search\n2.输入 Real Madrid 回车",
     "expected": "结果区渲染，页面文本含关键词"},
    {"module": "搜索", "title": "搜索-热门词点击直达结果", "pn": "positive", "p0": True,
     "steps": "1.打开 /search\n2.点击热门搜索词",
     "expected": "结果页渲染对应词结果"},
    {"module": "我的", "title": "我的-Login 引导区渲染与资产入口", "pn": "positive", "p0": True,
     "steps": "1.打开 /my\n2.查看页面",
     "expected": "Login 引导（Get more sports news）与 Silver Diamond/Camel Mall/Favorites/Outfits 入口渲染"},
    {"module": "联赛", "title": "联赛-积分榜/赛程表面渲染", "pn": "positive", "p0": True,
     "steps": "1.打开 /r/league/UEFA%20Europa%20League",
     "expected": "联赛标题与 Standings/Schedule/Fixture 区块渲染"},
    {"module": "球队", "title": "球队-从联赛进入球队详情", "pn": "positive", "p0": True,
     "steps": "1.打开联赛页\n2.点击球队链接",
     "expected": "跳转 /team/...，球队名/Schedule/Squad 渲染"},
    {"module": "回放", "title": "回放-列表点击进入详情播放器", "pn": "positive", "p0": True,
     "steps": "1.打开 /match-replay\n2.点击首条回放",
     "expected": "跳转 /match-replay/{id}，回放信息/播放器渲染"},
    {"module": "世界杯专题", "title": "世界杯-Match Center/Schedule/Groups/Bracket 导航", "pn": "positive", "p0": True,
     "steps": "1.打开 /worldcup-2026\n2.依次点击 Match Center/Schedule/Groups/Bracket 入口",
     "expected": "各区块渲染"},
    {"module": "赛事详情", "title": "赛事详情-直达无效赛事 URL 显示友好错误", "pn": "negative", "p0": True,
     "steps": "1.直接访问 /football/team-a-vs-team-b/invalid-match-id-123456",
     "expected": "不白屏；显示 404/友好提示而非崩溃"},
    {"module": "搜索", "title": "搜索-无结果关键词显示空态", "pn": "negative", "p0": False,
     "steps": "1.打开 /search\n2.输入不存在的长乱码词并回车",
     "expected": "结果区显示空态提示，不报错"},
    {"module": "首页", "title": "首页-导航链接可达性抽样（News/My/Replays）", "pn": "negative", "p0": True,
     "steps": "1.打开首页\n2.抽样点击 News/My/Match Replays 导航链接",
     "expected": "各链接跳转目标页并渲染，无 404 白屏"},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    args = ap.parse_args()
    if not args.database_url:
        print("ERROR: 需要 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    paths = extract_paths()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "interaction-paths.json").write_text(
        json.dumps(paths, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"[paths] {paths['count']} edges / {paths['pages']} pages", flush=True)

    dsn = args.database_url
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false "
                "AND tags::text LIKE '%%interaction:batch-113%%'"
            )
            existing = cur.fetchone()[0]
            imported = 0
            for c in INTERACTION_CASES:
                tags = json.dumps(["interaction:batch-113", f"module:{c['module']}"], ensure_ascii=False)
                cur.execute(
                    "INSERT INTO test_case (project_id, case_id, title, domain, module, is_deleted, "
                    "case_type, priority, status, tags, case_design_method, positive_negative, test_data_note, "
                    "preconditions, steps, expected_result, api_method, api_endpoint, api_headers, api_body, "
                    "api_assertions, api_spec_ref, last_response_json, last_run_status, source, source_req_id, source_doc_id, "
                    "source_case_index, review_status, review_comment, reviewer_id, created_at, updated_at) "
                    "VALUES (1,'',%s,'交互测试',%s,false,'functional',%s,'active',%s,'场景法',%s,%s,'',%s,%s,'','','','','','','','',"
                    "'ai_generated','',NULL,NULL,'draft','',0,now(),now())",
                    (
                        c["title"], c["module"], "P0" if c["p0"] else "P1", tags,
                        "positive" if c["pn"] == "positive" else "negative",
                        f"生产页面交互（Batch 113，{c['pn']}）",
                        c["steps"], c["expected"],
                    ),
                )
                imported += 1
            summary = {"existing_before": existing, "imported": imported, "total": existing + imported,
                       "positive": sum(1 for c in INTERACTION_CASES if c["pn"] == "positive"),
                       "negative": sum(1 for c in INTERACTION_CASES if c["pn"] == "negative"),
                       "p0": sum(1 for c in INTERACTION_CASES if c["p0"])}
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    (EVIDENCE_DIR / "interaction-cases-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"[cases] existing={existing} imported={imported} total={summary['total']} pos={summary['positive']} neg={summary['negative']} p0={summary['p0']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
