# 体育平台 P0 功能用例 → UI 自动化映射（Batch 110）

> 原则：UI 自动化基于**功能用例 P0** 梳理和执行；生产只读（GET/HEAD + 查询型 POST 白名单）；
> 写型端点（支付/下单/收藏/点赞/评论等）一律拦截并记录。

## 0. P0 口径（Batch 111 用户确认，2026-08-06；P0=390 条 / 33 域 / 151 模块）

**用户端 P0 域**（全部 P0）：首页、赛事详情、直播间、资讯、搜索、登录注册、个人中心、
广告系统、启动引导（开屏广告/跳过广告）、APP端数据与排行榜（联赛详情页/球队详情页/球员详情页/榜）、
回放（Batch 111 补：回放列表/回放详情）。

**运营后台 P0 模块**（其余 P1）：
| 域 | P0 模块 |
|---|--------|
| 财务管理 | 用户账户、充值记录、提现管理、提现审核、数字货币充值配置 |
| 赛事预测 | 预测赛事列表、新增/编辑预测赛事、用户参与记录、奖励发放记录、退回记录、风控设置 |
| UGC管理 | 文章列表/创建/编辑/分类/搜索/状态流转/统计、创作者管理、购买记录查询 |
| 商城管理 | 商品列表/新增编辑/上下架/删除/搜索筛选、购买记录查询 |
| 广告管理 | 广告位管理、广告活动管理、广告活动状态控制、新增/编辑广告活动 |
| 装扮管理 | 头像框、勋章 |
| 消息管理 | 聊天室消息、推送消息 |
| 球队及联赛管理 | 热门联赛、屏蔽赛事视频（Batch 111 补） |
| 用户管理 | 用户列表、用户封禁、屏蔽记录、举报记录、意见反馈（Batch 111 补） |
| 风控管理 | 头像图片监控/审核/违规处理、文案白名单（整域 P0） |
| 银钻任务管理 | 任务内容列表、任务完成记录、邀请好友记录 |
| 系统管理 | 版本更新 |

> 口径核对证据：`evidence/batch-111/p0-inventory.json`（390 条按域/模块分布）。

## 1. P0 功能用例基线（用户端关键用户路径）

| # | P0 功能用例（域-模块-场景） | 生产页面 | 核心接口（真实样本） |
|---|---------------------------|---------|--------------------|
| 1 | 用户端-首页-直播列表加载 | `/` Live Matches | `sports_live/hot_match`、`hot_group_match` |
| 2 | 用户端-首页-广告位展示 | `/` INDEX Banner | `ads/activity/get` |
| 3 | 用户端-首页-客户端初始化 | `/` 任意页 | `client/general` |
| 4 | 用户端-赛事详情-页面元素 | `/football/{id}` | `match/analysis`、`lineup`、`team_stats/list`、`time` |
| 5 | 用户端-赛事详情-赔率展示 | `/football/{id}` | `forecast/queryOddsSummaryByMatchId` |
| 6 | 用户端-直播间-直播页渲染 | `/football/.../live/` | `loadAnchorsByMatchId`、`view_match` |
| 7 | 用户端-直播间-聊天室历史 | 直播间 | `client/getHistoryMessage` |
| 8 | 用户端-资讯-列表与详情 | `/q/news`、`/news/detail/{id}` | `news/list_visible`、`news/get_visible`、`news/get`、`news/related` |
| 9 | 用户端-搜索-热门词与结果 | `/search` | `search/hot`、`search/query`、`search/recommend` |
| 10 | 用户端-我的-登录引导与资产入口 | `/my` | `login/anonymous/web`、`getCountryCode` |
| 11 | 用户端-联赛-积分榜/赛程 | `/r/league/{name}`、`/league/{name}` | `season/match`、`season/recent/table/detail` |
| 12 | 用户端-球队-页面渲染 | `/team/{name}/{id}` | `get_team_by_name` |
| 13 | 用户端-回放-列表与详情 | `/match-replay`、`/match-replay/{id}` | `replay/list`、`replay/get` |
| 14 | 用户端-世界杯-专题 | `/worldcup-2026` | `fifa/football/season/match`、`konfi getDataById` |
| 15 | 用户端-公共-首页加载性能 | `/` | —（15s 基线） |

## 2. UI 自动化映射（spec ↔ 用例）

| UI spec | 覆盖 P0 用例 | 断言要点 | 只读守卫 |
|---------|-------------|---------|---------|
| P0-UI-001 首页 | #1 #2 #3 | Live Matches 区块、搜索框、REGISTER、核心 API 资产命中 | GET + 查询 POST 白名单 |
| P0-UI-002 赛事详情 | #4 | 标题/比分/标签渲染 | 同上 |
| P0-UI-003 直播间 | #6 #7 | 视频容器/直播元素 | 同上 |
| P0-UI-004 资讯 | #8 | 列表 + 详情链接 | 同上 |
| P0-UI-005 搜索 | #9 | 输入查询 → 结果渲染 | 同上（放行 search/query） |
| P0-UI-006 我的 | #10 | Login 引导 + 资产/功能入口 | 同上（放行匿名登录查询） |
| P0-UI-007 联赛 | #11 | 联赛名 + Standings/Schedule 表面 | 同上 |
| P0-UI-008 回放 | #13 | 回放列表链接 | 同上 |
| P0-UI-009 世界杯 | #14 | Match Center/Schedule/Groups/Bracket | 同上（放行 konfi 读取） |
| P0-UI-010 性能 | #15 | 首页 load <15s | 同上 |

## 3. 执行方式

```bash
cd test-platform-v2/backend/tests/playwright
$env:BASE_URL="https://www.camel1.tv"
$env:PROD_ALLOWED_HOSTS="www.camel1.tv,api.cameltv.live,livecdn.cameltv.live,img.cameltv.live,sensors.cameltv.live"
$env:PROD_EXPECTED_BUSINESS_TEXT="Football Today - Watch Live Streaming"
$env:PROD_SMOKE_OWNER="sports-integration"
npx playwright test production-p0-modules.spec.ts --project=chromium --reporter=list,html
```

> 守卫：非白名单 POST（支付/下单/收藏/评论等写路径）会被 `assertP0RequestAllowed` 拦截并记为失败，
> 保证生产只读（C101-1 口径：真实拦截为发现，不静默放行）。

## 4. 证据

- 执行报告与截图：`work-logs/evidence/batch-110/ui-automation/`（report.json/html + 截图）
- 控制台错误与拒绝列表随报告落盘
