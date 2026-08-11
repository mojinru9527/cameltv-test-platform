# Batch 150 — 请求缓存/防抖/退避 + mindmap 聚合（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 引入新行为（client 会话级缓存/去重、轮询退避、mindmap 数据源切换为 taxonomy 聚合），属重构+新行为，完整批次。
非目标: 统计口径（149 已完成）、功能用例入计划与失败自动链路（Batch 151）、文档/图谱/空白机（Batch 152+）；不改后端统计/知识图谱。

## 0. 背景与来源
- 来源：`docs/batch-147-issue-landing.md` FIX-147-P1-03，承接 **C147-5**（并承接 C146-3）。
- 现状（生产 2026-08-11）：menus×53、environments×6、domains×4、defect 搜索 14 键 14 请求、mindmap 10.1MB（page_size=10000）、integration 两处 page_size=1 探针。

## 1. 问题陈述
1. 菜单/环境/域等低频静态数据随布局/页面挂载重复拉取，无会话级缓存与去重。
2. 搜索框每次按键即发请求（defect 14 键 14 请求），无防抖。
3. 性能监控轮询固定 500ms，失败/空数据时无退避。
4. mindmap 一次拉全量用例（page_size=10000，10.1MB）；后端已有 `/test-cases/taxonomy` 服务端聚合未使用。
5. integration 用 `page_size=1` 探针判断有无用例，浪费请求。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| menus/environments/domains 请求数 | 53/6/4 | ≤1（会话内） | Network 面板 |
| 搜索请求 | 每键 1 次 | 300ms 防抖合并 | Network 面板 |
| 轮询 | 500ms 固定 | 指数退避（500ms→30s 上限），有数据即复位 | 代码 + 冒烟 |
| mindmap 传输 | 10.1MB | taxonomy 聚合（KB 级） | Network 面板 |
| integration 探针 | 2 次 page_size=1 | 0（改用 stats） | 代码 |

## 3. 用户故事 + 验收标准
- As 平台用户, I want 重复访问同一页面不再重复拉取菜单/环境/域, so that 加载更快、网络更干净。
- As 平台用户, I want 搜索停顿后才发请求, so that 不因快速输入打爆接口。
- As 性能监控用户, I want 轮询在无数据时自动放慢, so that 不空转请求。
- As 平台用户, I want 脑图不再下载全量用例, so that 打开快、流量小。
- 验收：Network 面板三项低频数据 ≤1 次；脑图响应为 taxonomy（KB 级）且结构与原来一致（界面→域→模块→计数）。

## 4. 技术考量
- client.ts 增加 `cachedGet(url, params, {ttl, force})`：会话级 Map 缓存 + 进行中请求去重；`clearApiCache(prefix)` 供 401/登出/变更后清理。
- fetchMenus/fetchEnvironments/fetchDomains 改为 cachedGet（TTL 60s）；环境/域 CRUD 后 clearApiCache。
- 新增 `useDebouncedValue` hook（300ms），defect 搜索接入。
- `usePerfWebSocket` 轮询改自适应 setTimeout 链：500ms 起步，空/失败 ×2，上限 30s，有数据复位。
- mindmap 改用 `fetchTaxonomy`（服务端聚合），前端按 surface/domain 过滤，树渲染计数；保留标题计数展示。
- integration 探针改 `fetchTestCaseStats().total`。
- 风险：缓存导致数据陈旧 → TTL 60s + CRUD 清理；signal 传参时走原路径不缓存。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 用户 | Network 计数下降 + 脑图可用 |

## 6. 技能使用
- cameltv-bug-guard（防 N+1/重复请求、useEffect 清理）
- cameltv-ui-conventions（Select/搜索交互基线）
