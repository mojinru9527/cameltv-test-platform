# Batch 114 — Design Spec（交互拓扑 + UI 自动化 + 章节化）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

Playwright（`backend/tests/playwright`，只读守卫 production-p0-contract.ts，B112-4 已修复）；
脚本：`scripts/sports/*.py`；知识中心：标准 capture + RAG search。

## 1. 交互拓扑规格（C113-1）

输入：`evidence/batch-113/interaction-paths.json`（3172 边：from/from_module/entry/to）。
输出：`interaction-topology.json`：

```json
{"nodes": [{"id": "首页", "pages": ["/"], "p0": true}],
 "edges": [{"from": "首页", "to": "赛事详情", "entries": ["赛事卡片", "Live Matches"], "count": 42, "p0": true}]}
```

聚合规则：from_module→to_module 聚合边，入口合并去重，P0 模块优先标记；
文档 `docs/体育平台-交互拓扑.md` 用 mermaid 图呈现关键闭环。

## 2. 交互 UI 自动化 spec（C113-1）

`production-interaction.spec.ts`（复用 `guardP0` + `readP0Runtime`），用例（≥8）：

| # | 交互路径 | 断言 |
|---|---------|------|
| 1 | 首页 → 赛事详情（点赛事卡） | URL 含 /football/；标题/比分渲染 |
| 2 | 赛事详情 → 直播间（Watch Live） | URL 含 /live/；roomLive 容器可见 |
| 3 | 详情 → 返回 | 返回首页可交互 |
| 4 | 首页 → 回放列表 | URL /match-replay；列表链接渲染 |
| 5 | 回放列表 → 详情 | URL /match-replay/{id}；标题渲染 |
| 6 | 资讯列表 → 详情 | /news/detail/ 详情渲染 |
| 7 | 搜索 → 结果 | 输入关键词后结果含关键词 |
| 8 | 我的页面渲染 | Login 引导 + 资产入口可见 |

执行：本地 `npx playwright test production-interaction.spec.ts --project chromium`；
平台：新增/复用 UI job 绑定该 spec 触发核对。

## 3. 知识中心章节化（C113-2）

把关联基座按模块拆章节 capture（每模块一个 source：title=「体育平台-{模块}-模块关联（Batch 114）」，
content=该模块的接口/后台/konfi 关联）；检索验证：模块词（首页/直播间/回放/世界杯）命中对应章节 source。
既有 source#17 保留（追加不删除）。

## 4. 设计 QA 走查

### ⚪ P3-1 交互 spec 稳定性
赛事/回放数据为实时生产数据，元素可能随赛程变化。**建议**：断言用模块级文案（Live Streaming/比分区）
而非具体队名；本批已按此设计。

## 5. 设计签核

结论：**通过**（无 P0/P1 阻断项）。
