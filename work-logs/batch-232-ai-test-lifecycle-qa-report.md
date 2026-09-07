# Batch 232 - QA Report

> QA | Date: 2026-09-07 | Verdict: **PASS** for platform code; Mission 9101 business acceptance remains **FAIL**

## 结论

旧报告中的 PASS 已失效。它把“有任务容器/占位状态”误当成“有完整测试事实”，且没有检查资料片段、逐用例证据、Build/Campaign 和后续分析记录是否真实存在。

本批已修复这类假通过：生命周期状态现在只由持久化事实计算。Mission 9101 的事实链已完整展示，但 Test5 UI 自动化发现 11 个资源或控制台错误，因此该业务任务验收结论必须为 **FAIL / 未通过**，关联缺陷为 `B232-TEST5-001`。

平台代码与被测业务采用两个独立结论：测试平台正确发现并保留业务失败，不应反过来阻止测试平台自身修复发布。平台实现通过本地门禁后可进入 Draft PR；Mission 9101 在缺陷复验前不得改为通过，也不得作为 16.0.0 已验收的证据。

## AI 缓存成本专项

| 检查 | 结果 |
|---|---|
| OpenAI usage | `prompt_tokens_details.cached_tokens` 归一化为输入、命中、未命中、输出、命中率 |
| DeepSeek usage | `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` 归一化到同一口径 |
| OpenAI 缓存路由 | 仅 `api.openai.com` 发送稳定 `prompt_cache_key`；项目/提供方/模型/命名空间变化会隔离 |
| 兼容端点保护 | DeepSeek、GLM、Qwen 等非 OpenAI hostname 不发送专用字段 |
| 稳定前缀 | AITDE 阶段共用 1049 个英文词的业务规则前缀，动态需求置后；不是无意义填充 |
| 重复输出费用 | 歧义/意图完全相同请求由 2 次真实模型调用降为 1 次，第二次复用结构化结果 |
| 落库与展示 | AI 操作记录保存模型、Prompt 版本、耗时、输入哈希和真实 usage；抽屉显示中文指标 |
| 真实性边界 | 明确区分 0% 与未返回；空/畸形 usage 不合成 Token；不推算金额、不显示 Prompt/密钥/缓存键 |

## Mission 9101 事实清单

| 页面 | 已持久化内容 | QA 结论 |
|---|---|---|
| 资料 | 1 份需求资料，4 个非空需求片段 | 可追溯；空片段不可完成 |
| 范围 | 3 个已批准范围项：篮球首页功能、篮球首页赛事接口、篮球联赛详情导航 | 可追溯到需求片段 |
| 契约 | 冻结版本 v1，3 条规则、3 个必需产出 | 可追溯到范围/需求 |
| 场景 | 功能、接口、UI 自动化各 1 条；均含模块、需求角色和来源 | 三条用例均已执行 |
| 执行 | 3 次 Run、8 个步骤、8 个断言、6 个已验证物理证据、3 份回放清单 | 功能 PASS、接口 PASS、UI BUSINESS_FAIL |
| Build/验收 | Build #1、Campaign #1、Quality Gate 4/5 | G5 UI 资源错误为零未通过 |
| 变化检测 | 1 个变更集、3 个变更项 | 已分析 |
| 影响分析 | 1 次影响分析，命中 3 个场景 | 已完成 |
| Lineage | 6 条 Source → Scenario → Run 边 | 可追溯 |
| 场景缺口 | 1 个“第三方资源失败时的降级展示与生产复验”候选 | 待处理 |

## 被测结果

| 用例 | 类型 | 结果 | 证据/处置 |
|---|---|---|---|
| 篮球首页核心功能区展示 | 功能 | PASS | 截图 + 视频，2/2 证据已验证 |
| 篮球首页赛事接口返回分组数据 | 接口 | PASS | JSON + trace，2/2 证据已验证 |
| 从赛事列表进入 NBA 联赛详情 | UI 自动化 | BUSINESS_FAIL | 截图 + 视频，观察到 Google GSI 403、图片代理 503/504、NBA CDN HTTP2 错误；缺陷 `B232-TEST5-001` |

测试目标为 `https://camel-bball-test5.elelive.cn/basketball`。本地 Mission 只是将真实 Test5 执行证据录入隔离环境，不代表生产测试平台已经创建任务或已经发布。

## 平台实现验证

| 检查 | 结果 |
|---|---|
| 后端重点生命周期/证据/回放 | 29 passed |
| Alembic/迁移检查 | 11 passed；单一 head |
| 后端全量 | 2522 passed / 49 skipped / 1 xfailed / 0 failed |
| 前端重点 | 6 files / 9 passed |
| 前端全量 | 159 files / 695 passed |
| 静态与构建 | Ruff F821、typecheck、lint、production build 全通过 |
| 仓库门禁 | `PASS_WITH_WARN`；0 HARD / 332 WARN，G1/G2 通过 |
| 浏览器验收 | 16 个页面/视口检查；0 缺失、0 横向溢出、0 console error、0 failed request |
| 请求行为 | 12 个业务页逐页统计，0 个重复有效 GET；场景页复用 lifecycle 查询缓存 |
| AI 缓存重点 | 47 passed；覆盖 OpenAI/DeepSeek、同步/异步、去重、落库、0%/未知展示 |
| AI 缓存浏览器 | 桌面 1440×900、手机 390×844 无横向溢出；0 console error / 0 应用请求失败 |

49 个 skipped 依赖当前不可用的 PostgreSQL、Lanhu、Compose 或生产只读设施；1 个 xfail 是仓库已记录的 SQLite 全链降级限制。本批相关的 previous-head 升降级路径已通过。

## 浏览器证据

- 桌面逐页覆盖：概览、资料及片段、范围、契约、场景、执行、Build、验收、变化检测、影响分析、Lineage、场景缺口、Run 回放。
- 平板 `768x1024` 与手机 `390x844` 均等待“AI 六阶段主链”等业务文本出现后截图，不再接受加载动画作为证据。
- `browser-report.json` 记录每页期望内容、宽度、请求计数、重复 GET、控制台错误和失败请求。
- 物理执行证据包含功能/UI 的 PNG + WebM，以及 API 的 JSON + trace。

证据索引：`work-logs/evidence/batch-232-ai-test-lifecycle/index.md`。

## QA 打回项

| ID | 级别 | 问题 | 状态 |
|---|---|---|---|
| B232-QA-04 | P1 | Test5 UI 自动化出现 11 个资源/控制台错误，Gate G5 未通过 | OPEN，关联 `B232-TEST5-001` |
| B232-QA-05 | P1 | 旧 PASS 由空片段/占位事实推断，无法证明完整链路 | FIXED；生命周期改为事实驱动且旧 PASS 降为 `NOT_EVALUATED` |
| B232-QA-06 | P2 | 初版手机/平板截图停留在加载动画 | FIXED；增加业务内容等待并重新取证 |
| B232-QA-07 | P2 | 场景页重复请求 lifecycle | FIXED；共享 TanStack Query 缓存，逐页验证无重复 GET |

## 发布边界

- 当前只完成独立 worktree 的本地实现与 Mission 9101 验证，未推送、未建 PR、未合并、未部署生产。
- 平台代码发布与 Mission 9101 业务验收分离：前者可在仓库/发布门禁通过后上线，后者必须保持 FAIL 直到真实复验。
- 生产环境不得沿用历史 Mission 34 伪装为本次结果；发布后必须创建或关联真实 16.0.0 Mission。
- FEATURE / VERSION 阶段使用 Test5；REGRESSION 阶段只能在版本发布并获得生产执行确认后运行。
- 缺陷 `B232-TEST5-001` 修复后，必须沿原 Run 建立复验关系并重新评估 Gate。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 12h / 实际跨会话无法可靠计量 | 0/3/2/0 | 3 | 流程 + 外部依赖 + 成本可观测性 | Gate 必须验证非空事实和物理证据；AI 调用必须落真实 usage，并在设计时检查重复调用与稳定前缀 |

**Skills used**: Agent Team 管理六部门工件与门禁；Bug Guard 约束失败关闭、迁移和请求；UI conventions 约束中文状态与响应式；Playwright 提供可复现浏览器证据。
