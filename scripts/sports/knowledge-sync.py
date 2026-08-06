"""体育平台承接 — 知识中心内容直连同步（Batch 102）。

背景: 生产知识入库接口异常（/knowledge/capture 一律 409 且库中无来源，向量检索
非 functional），已登记为平台障碍。本脚本按平台 ingest_capture 同一落库语义
（source_type=capture, para_category=inbox, status=parsed + chunk_type=capture），
把 Batch 102 功能逻辑知识直连写入生产库；并补入功能模块图谱实体/关系
（用户端 ↔ 运营后台 ↔ konfi），供知识中心图谱可视化。

运行: <venv-python> scripts/sports/knowledge-sync.py --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-102"


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


SOURCES = [
    {
        "title": "体育平台-功能总览（用户端/运营后台/konfi）",
        "content": (
            "# 体育平台功能总览（Batch 102 梳理）\n"
            "平台三端：用户端（App/PC/Web，www.camel1.tv）、运营后台（管理端，生产账号不公开）、"
            "konfi（配置系统，契约待 Test5 恢复后补拉）。\n"
            "用户端核心：首页（Live Matches/Favorites/Competitions/Match Replays）、赛事详情"
            "（直播/赛况/数据/阵容/H2H/预测/Picks）、直播间（视频/动画/聊天室/打赏）、我的"
            "（账户/骆驼币/银钻/商城/装扮/FAQ）、UGC（文章/订阅/创作者）、资讯、搜索、世界杯专题页。\n"
            "运营后台核心：财务（账户/充值/流水/提现/风控）、赛事预测（赛事管理/用户参与/结算/退回/统计）、"
            "UGC（文章/创作者/分类/统计）、内容管理（资讯/FAQ/热门搜索）、商城（商品/购买记录）、"
            "广告（活动/素材/广告位）、装扮（头像框/勋章）、消息（聊天室/推送）、用户管理（列表/封禁/屏蔽/举报）、"
            "系统（版本更新）、赛事视频流/推流主播。\n"
            "konfi：负责平台配置项下发（广告位/活动/直播源/装扮等），与运营后台管理页联动；"
            "具体契约待 Test5 环境恢复后补拉（C95-1/C74-2）。"
        ),
    },
    {
        "title": "体育平台-用户端模块地图（需求↔生产）",
        "content": (
            "# 用户端模块地图\n"
            "需求文档：蓝湖原型-用户端原型（98 页，14.1.0）；生产验证：www.camel1.tv 真实浏览器勘察（2026-08-06）。\n"
            "- 首页 /：Live Matches、Favorites、Competitions、Match Replays、World Cup 2026。用例域：首页/应用启动/广告。\n"
            "- 赛事详情 /football/{home}-vs-{away}/{id}：直播流、赛况比分、数据统计、阵容 Lineup、H2H、"
            "赛程 Schedule、赔率 Odds、预测 Prediction、Picks。用例域：赛事详情。\n"
            "- 直播间 /football/.../live/{id}：视频播放、动画直播、聊天室、打赏、用户资料卡。用例域：赛事详情-聊天室/视频直播。\n"
            "- 我的 /my：登录注册、骆驼币账户、银钻账户、Camel 商城、我的收藏、我的资料、FAQ、意见反馈、我的装扮、"
            "创作者中心（每日收益/提现）。用例域：用户账户/银钻任务/商城/装扮。\n"
            "- UGC：文章列表/详情/解锁/创作者主页；订阅与购买记录。用例域：UGC。\n"
            "- 资讯 /q/news、资讯详情 /news/detail/...；搜索 /search（热门：Premier League/Real Madrid 等）；"
            "联赛 /r/league/、球队 /team/；回放 /match-replay；世界杯 /worldcup-2026。\n"
            "- 说明附件：广告位系统、银钻系统、银钻预测玩法、UGC 功能概述、邀请活动、骆驼币及绿钻规则。"
        ),
    },
    {
        "title": "体育平台-运营后台模块地图（需求文档）",
        "content": (
            "# 运营后台模块地图\n"
            "需求文档：蓝湖原型-运营后台原型（72 页，8.2.0）。\n"
            "- 财务（11 页）：用户账户、账户详情、充值记录、骆驼币流水、银钻流水、提现管理（待打款/已拒绝）、"
            "提现流水、充值商品管理（套餐/数字货币）。\n"
            "- 赛事预测（7 页）：预测赛事列表、新增/编辑、用户参与记录、奖励发放记录、退回记录、数据统计（用户统计）、风控设置。\n"
            "- UGC（9 页）：文章列表/创建/查看、订阅记录、文章购买记录、创作者列表、文章分类管理、数据统计（文章统计）。\n"
            "- 内容管理（7 页）：资讯列表/查看/新增编辑、资讯分类、热门搜索管理、FAQ 管理。\n"
            "- 商城（3 页）：商品管理、新增/编辑商品、购买记录。\n"
            "- 广告（5 页）：广告活动管理、广告素材管理、广告位管理。\n"
            "- 装扮（5 页）：头像框（新增编辑/关联用户）、勋章（新增编辑）。\n"
            "- 消息（4 页）：聊天室消息、推送消息。\n"
            "- 球队及联赛（4 页）：热门联赛、热门球队、屏蔽赛事视频。\n"
            "- 用户管理（5 页）：用户列表、封禁记录、屏蔽记录、举报记录、意见反馈。\n"
            "- 根目录：更新日志、赛事视频流、推流主播。\n"
            "- 系统管理（1 页）：版本更新。"
        ),
    },
    {
        "title": "体育平台-生产页面与需求对照（勘察记录）",
        "content": (
            "# 生产页面勘察记录（2026-08-06，www.camel1.tv）\n"
            "真实浏览器（Chromium 1440x900）采集 10 页面：home、/q/news、/my、/football/{match}、/r/league/、/team/、"
            "/football/.../live/、/match-replay、/worldcup-2026、/search。\n"
            "生产为英文站（EN-English），与需求中文原型存在文案/入口差异（生产无显式 UGC 入口、含 World Cup 2026 专题与 Match Replays）。\n"
            "站点含第三方广告域与 POST 信标（Batch 101 C101-1 登记）。\n"
            "证据：test-platform-v2/work-logs/evidence/batch-102/production-walkthrough/（JSON + 截图）。"
        ),
    },
    {
        "title": "体育平台-konfi 配置关联（待校准）",
        "content": (
            "# konfi 配置关联（第一期推断，待 Test5 校准）\n"
            "konfi 为体育平台配置系统（登录 API /konfiapi/user/login，账号 test-cameltv 已登记 C74-2）。\n"
            "推断关联：运营后台「广告位管理/广告活动」→ konfi 广告位配置；「赛事视频流/推流主播」→ konfi 直播源配置；"
            "「充值赠币活动」→ konfi 活动配置；「装扮（头像框/勋章）」→ konfi 装扮配置；「热门搜索管理」→ konfi 搜索热词配置。\n"
            "解除条件：Test5 环境恢复 + konfi 密码落位后补拉契约（C95-1），以真实接口校准本映射。"
        ),
    },
]

# 图谱实体与关系（用户端 ↔ 运营后台 ↔ konfi）
ENTITIES = [
    ("module", "user:home", "用户端-首页", "直播列表/收藏/赛事/回放/世界杯入口"),
    ("module", "user:match", "用户端-赛事详情", "直播/赛况/数据/阵容/H2H/赔率/预测/Picks"),
    ("module", "user:live", "用户端-直播间", "视频/动画/聊天室/打赏/用户资料卡"),
    ("module", "user:mine", "用户端-我的", "账户/骆驼币/银钻/商城/装扮/FAQ/创作者中心"),
    ("module", "user:ugc", "用户端-UGC", "文章列表/详情/解锁/创作者主页"),
    ("module", "user:news", "用户端-资讯", "资讯列表/详情/搜索"),
    ("module", "admin:finance", "运营后台-财务", "账户/充值/流水/提现/风控"),
    ("module", "admin:predict", "运营后台-赛事预测", "预测赛事/参与/结算/退回/统计/风控"),
    ("module", "admin:ugc", "运营后台-UGC管理", "文章/创作者/分类/统计"),
    ("module", "admin:content", "运营后台-内容管理", "资讯/FAQ/热门搜索"),
    ("module", "admin:shop", "运营后台-商城", "商品/购买记录"),
    ("module", "admin:ad", "运营后台-广告管理", "活动/素材/广告位"),
    ("module", "admin:dress", "运营后台-装扮管理", "头像框/勋章/关联用户"),
    ("module", "admin:stream", "运营后台-赛事视频流/推流主播", "直播源管理"),
    ("module", "admin:user", "运营后台-用户管理", "列表/封禁/屏蔽/举报/意见反馈"),
    ("module", "konfi:config", "konfi-配置系统", "广告位/活动/直播源/装扮/搜索热词配置下发"),
]

RELATIONS = [
    ("user:live", "admin:stream", "managed_by", "直播间直播源由运营后台赛事视频流/推流主播管理"),
    ("user:match", "admin:predict", "managed_by", "赛事预测/Picks 由运营后台赛事预测管理"),
    ("user:ugc", "admin:ugc", "managed_by", "UGC 文章/创作者由运营后台 UGC 管理"),
    ("user:news", "admin:content", "managed_by", "资讯/FAQ 由运营后台内容管理"),
    ("user:mine", "admin:finance", "managed_by", "账户/资产由运营后台财务模块管理"),
    ("user:mine", "admin:shop", "managed_by", "商城商品由运营后台商城管理"),
    ("user:mine", "admin:dress", "managed_by", "装扮（头像框/勋章）由运营后台装扮管理"),
    ("user:home", "admin:ad", "managed_by", "首页广告位由运营后台广告管理"),
    ("admin:ad", "konfi:config", "configures", "广告位/活动配置经 konfi 下发"),
    ("admin:stream", "konfi:config", "configures", "直播源配置经 konfi 下发"),
    ("admin:dress", "konfi:config", "configures", "装扮配置经 konfi 下发"),
    ("admin:content", "konfi:config", "configures", "热门搜索热词经 konfi 下发"),
    ("admin:predict", "konfi:config", "configures", "赛事预测风控/结算配置经 konfi 下发"),
    ("user:live", "user:match", "contains", "直播间属于赛事详情"),
    ("user:ugc", "user:mine", "contains", "创作者中心/我的 UGC 入口"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    args = ap.parse_args()
    if not args.database_url:
        print("ERROR: 需要 --database-url / TP_DATABASE_URL", flush=True)
        return 1
    dsn = args.database_url
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    now = _now()
    created_sources = 0
    created_chunks = 0
    created_entities = 0
    created_relations = 0
    try:
        with conn.cursor() as cur:
            for s in SOURCES:
                full = f"# {s['title']}\n\n{s['content']}"
                chash = _h(full)
                cur.execute(
                    "SELECT id FROM knowledge_source WHERE project_id=1 AND source_type='capture' "
                    "AND source_id IS NULL AND content_hash=%s",
                    (chash,),
                )
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO knowledge_source (project_id, source_type, source_id, title, source_ref, "
                    "content_hash, version, iteration_id, para_category, knowledge_domain, freshness_score, "
                    "status, raw_content, metadata_json, module_name, module_id, last_verified_at, created_at, updated_at) "
                    "VALUES (1,'capture',NULL,%s,'',%s,'',NULL,'inbox','platform',1.0,'parsed',%s,'{}','体育平台',NULL,%s,%s,%s) "
                    "RETURNING id",
                    (s["title"], chash, full, now, now, now),
                )
                src_id = cur.fetchone()[0]
                created_sources += 1
                chunk_full = full
                cur.execute(
                    "INSERT INTO knowledge_chunk (project_id, source_id, chunk_type, title, content, content_hash, "
                    "token_count, embedding_id, tags, status, created_at) "
                    "VALUES (1,%s,'capture',%s,%s,%s,0,'','[]','active',%s) RETURNING id",
                    (src_id, s["title"], chunk_full, _h(chunk_full), now),
                )
                created_chunks += 1

            ent_ids: dict[str, int] = {}
            for etype, ekey, name, desc in ENTITIES:
                cur.execute(
                    "SELECT id FROM knowledge_entity WHERE project_id=1 AND entity_key=%s",
                    (ekey,),
                )
                row = cur.fetchone()
                if row:
                    ent_ids[ekey] = row[0]
                    continue
                cur.execute(
                    "INSERT INTO knowledge_entity (project_id, entity_type, entity_key, name, description, "
                    "source_id, business_ref_type, business_ref_id, confidence, review_status, metadata_json, "
                    "created_at, updated_at) VALUES (1,%s,%s,%s,%s,NULL,'',NULL,1.0,'approved','{}',%s,%s) RETURNING id",
                    (etype, ekey, name, desc, now, now),
                )
                ent_ids[ekey] = cur.fetchone()[0]
                created_entities += 1

            for from_key, to_key, rtype, desc in RELATIONS:
                fid = ent_ids.get(from_key)
                tid = ent_ids.get(to_key)
                if not fid or not tid:
                    continue
                cur.execute(
                    "SELECT id FROM knowledge_relation WHERE project_id=1 AND from_entity_id=%s "
                    "AND to_entity_id=%s AND relation_type=%s",
                    (fid, tid, rtype),
                )
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO knowledge_relation (project_id, from_entity_id, relation_type, to_entity_id, "
                    "confidence, evidence_chunk_ids, review_status, metadata_json, created_at) "
                    "VALUES (1,%s,%s,%s,1.0,'[]','approved',%s,%s)",
                    (fid, rtype, tid, json.dumps({"note": desc}, ensure_ascii=False), now),
                )
                created_relations += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "knowledge-sync-summary.json"
    out.write_text(
        json.dumps({
            "sources": created_sources,
            "chunks": created_chunks,
            "entities": created_entities,
            "relations": created_relations,
            "note": "生产 /knowledge/capture 接口异常（一律 409），按 ingest_capture 落库语义直连写入",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[db] sources={created_sources} chunks={created_chunks} entities={created_entities} relations={created_relations}", flush=True)
    print(f"[evidence] {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
