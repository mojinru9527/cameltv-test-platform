# Batch 113 — Design Spec（关联基座 + 知识中心入库 + 交互用例）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

后端/平台：知识中心 capture 通道（`/knowledge/capture`，C110-2 已验证）+ RAG 检索；
脚本：repo 根 `scripts/sports/*.py`（httpx + psycopg2，Batch 110-112 同目录约定）；
用例规范：`tests/test-case-standards/`（功能用例正负向/步骤/预期/P0）。
前端：本批无 React 改动。

## 1. 关联基座数据模型（`sports-module-interface-function-map.json`）

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-07",
  "sources": ["功能模块地图 v2", "evidence/batch-110/*"],
  "modules": [
    {
      "module_id": "user-home",
      "end": "user",
      "module": "首页",
      "page": "/",
      "functions": ["Live Matches 三 Tab", "Match Replays 区块", "World Cup 2026 区块", "新闻区块", "搜索/注册/帮助入口"],
      "interfaces": [
        {"method": "GET", "path": "/camel-service/ee/sports_live/hot_match", "params": "page=1&size=10",
         "sample": "evidence/batch-110/xhr-samples/xhr-samples-final.json", "function": "首页热门赛事"}
      ],
      "backend": ["运营后台-热门联赛/热门球队/广告位"],
      "konfi": ["sports_live_hot_competition", "sports_live_competition_agg_page"]
    }
  ]
}
```

覆盖：用户端 13 模块（§2）+ 运营后台 15 模块（§3）+ konfi 82 配置项关联（§4）+ 34 接口↔模块映射（§5）。
每个 module 的 interface/backend/konfi 字段与 evidence 交叉核对，无编造项。

## 2. 知识中心入库规格

- 导入内容：功能模块地图 v2 全文 + 关联基座 JSON（转 Markdown 章节化）。
- 通道：`POST /knowledge/capture`（复用 Batch 108/110 修复后的标准 capture）。
- 验证：`GET /knowledge/sources` 可见新 source；RAG 检索关键词（如 `sports_live_hot_competition`、
  `/camel-service/ee/sports_live/hot_match`、`世界杯专题`）命中关联内容。
- 证据：`evidence/batch-113/knowledge-association-summary.json`（capture code/id、sources、检索命中）。

## 3. 交互路径提取规格

输入：`production-walkthrough-v2/production-pages.json`（40 页 title/url/headings）+
`xhr-samples-final.json`（page 字段标识来源页）+ 功能地图 §2 页面列。
输出：`evidence/batch-113/interaction-paths.json`：

```json
{"paths": [
  {"from": "首页 /", "entry": "赛事卡片", "to": "/football/{home}-vs-{away}/{id}", "module": "赛事详情",
   "evidence": "production-pages.json + xhr page 来源", "p0": true}
]}
```

P0 模块优先：首页/赛事详情/直播间/资讯/搜索/我的/联赛/球队/回放/世界杯。

## 4. 交互用例生成规格（C112-2）

- 域：`交互测试`（domain 字段）+ 原模块名；case_type=functional；tags 含 `interaction:batch-113`。
- 正向：入口可达（Given 首页 / When 点击赛事卡片 / Then 进入赛事详情页并渲染标题/比分）；
  跳转成功；返回/回退；跨模块导航（详情→直播间、列表→详情、搜索→结果→详情）。
- 负向：直达无效 URL（404 页/友好提示）；空态（无数据区块）；断链入口（href 缺失/404）。
- 每条：前置/步骤（含点击跳转）/预期结果/正负向/P0 标识/设计方法（场景法）。
- 落库：复用 Batch 103 功能用例落库通道（直连库 INSERT 或平台 API），先核对既有用例域避免重复。
- 数量：≥15 条（P0 模块全覆盖，正 ≥10 / 负 ≥5）。
- 证据：`evidence/batch-113/interaction-cases-summary.json`（按模块/正负向统计 + 抽样核对）。

## 5. 设计 QA 走查发现

本批无前端 UI 改动；走查聚焦数据一致性：

### ⚪ P3-1 知识中心 source 内容结构
功能地图全文导入为单一 source，检索粒度粗。**建议**：章节化导入（每模块一段），后续可拆细；
本批不阻塞（关联基座 JSON 提供结构化检索路径）。

## 6. 设计签核

结论：**通过**（无 P0/P1 阻断项；source 粒度 P3 建议）。
