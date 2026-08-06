# Batch 110 — PRD（体育平台第一期收口：全模块逻辑 + P0 用例 + 接口用例/测试 + UI 自动化 + RAG/Wiki 知识库）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: full
豁免理由: 无（本期引入生产 wiki 能力启用、需求模块树直建脚本、接口真实样本批量采集与接口/UI 自动化执行，走完整六部门流水线）。
非目标:
- Test5 内网验收（C95-1/C74-2 继续 Deferred；konfi 契约校准仍待环境恢复）
- 运营后台生产登录账号（生产账号不公开，C101/C31-3 口径维持，以需求文档+测试环境为准）
- 需求 AI 提取/生成的异步化全量改造（C102-1 继续 Open，本期沿用本地生成+同步通道，仅登记）
- 生产页面与需求原型差异的「平台内标注 UI」开发（C102-4 继续 Open，本期以功能地图 v2 差异矩阵 + vision 识图走查落地）
- 性能采集优化（C99-1 跟踪）、iOS 真机（CP-C2/C84-1）、平台发布门禁（OPS0-3）
- 外部 LLM-Wiki 连接器（external_llm_wiki_enabled 保持 OFF）
- match replays 真实回放 URL 专项（C101-2 待业务提供）
- 运营后台生产页面勘察（不可达）；本期以 72 页需求文档 + 测试环境原型为主
```

## 1. 问题陈述

Batch 101–103 已完成体育平台承接的骨架：7 服务 899 端点契约导入、325+ 接口用例、4 份需求文档导入、
功能用例 476 条（用户端 227 / 运营后台 249）、知识中心 5 源/16 实体/15 关系、接口用例可视
（请求参数/断言/结果三栏）。但按用户第一期目标「梳理好体育平台的所有功能模块，尽可能覆盖现有所有逻辑」仍有明确缺口：

1. **功能模块覆盖不完整**：batch-102 生产勘察仅 10 页（home/news/my/match/live/league/team/replay/search/worldcup），
   用户端「我的」23 页、登录注册、支付充值、UGC、消息等未覆盖；运营后台「消息/球队及联赛/用户管理/系统管理」
   用例域仍为「待补」；konfi 关联仍是推断待校准。
2. **需求与实际逻辑的联动不足**：需求中文原型（98+72 页）与生产英文站（www.camel1.tv）存在文案/入口/新增模块差异，
   尚无系统性「需求页 ↔ 生产模块 ↔ 用例 ↔ 后台 ↔ konfi」的全量对照与差异标注。
3. **接口用例覆盖面过窄**：batch-103 仅有 3 个真实样本接口（list_visible/ads-activity/client-general）72 条字段级用例，
   C103-5 要求真实业务样本批量采集覆盖核心功能接口（首页/赛事/直播/我的/资讯/搜索等）≥20 个。
4. **接口测试未实跑**：接口用例已生成但未以生产真实请求执行并回填响应（C103-2/C103-7 的「请求结果」栏未填）。
5. **UI 自动化尚未基于功能用例落地**：现有 UI 自动化以 Test5 内网为主（tests/automation/ui），
   生产只读 UI 冒烟 3/5 通过；缺少「功能用例 P0 → UI 自动化」的显式映射与生产执行。
6. **RAG 与 Wiki 知识库未重度使用**：RAG 知识中心已建 5 源，但需求文档全文/功能地图/接口规范未全部入库；
   Wiki 知识库（Raw Source → 编译 → 差异对比）在生产未启用，体育平台无需求模块树与 Wiki 基线，
   无法支撑后续「不同版本之间的迭代更新」差异对比。
7. **平台使用障碍已积累**：C102-1~5、C103-6/7、C107-2 及本期新增障碍需持续登记，供后续逐批迭代。

用户同时指出：**已接入识图能力**，应把生产页面截图交给视觉模型做模块/逻辑走查，补强「需求 vs 生产」的差异与逻辑补充；
**接口自动化/接口测试**直接仿照生产接口已有的请求参数和响应结果（响应结果做断言）；
**UI 自动化基于功能用例 P0 用例来梳理和执行**。

## 2. 成功指标

| 指标 | 基线（2026-08-06 生产） | 目标 |
|------|------------------------|------|
| 生产页面勘察 | 10 页 | 用户端全路由 ≥25 页（含登录/我的全子页/支付充值/搜索/联赛/球队/回放/世界杯），JSON+截图证据 |
| 识图走查 | 无 | 生产截图 vision 走查覆盖主要页面，输出页面功能/差异描述（差异 JSON） |
| 功能模块地图 | v1（10 页矩阵，3 域待补） | v2：用户端/运营后台全模块矩阵 + konfi 关联更新 + 差异标注（需求 vs 生产） |
| 功能用例 | 用户端 227 / 运营后台 249 | 补齐待补模块；P0 用例标识 ≥30 条（UI 自动化基线，优先级字段落库） |
| 接口真实样本 | 3 个接口 | ≥20 个核心接口（首页/赛事/直播/我的/资讯/搜索/回放/世界杯/广告/客户端配置等） |
| 接口用例 | 72 条（3 接口） | 全字段字段级生成，覆盖 ≥20 接口；响应结构/关键字段断言可见 |
| 接口测试执行 | 未执行 | 核心接口 ≥10 个以真实请求实跑，last_response_json 回填（响应做断言） |
| UI 自动化 | 生产冒烟 3/5 | P0 用例 → UI spec ≥8 条生产只读执行通过 + 截图证据 |
| RAG 知识中心 | 5 源/16 实体/15 关系 | 需求文档 4 份全文 + 功能地图 + 接口规范入库（sources 可见）；图谱实体/关系扩展 |
| Wiki 知识库 | 生产未启用 | WIKI_ENABLED 启用；需求模块树直建 + raw sources + 编译页面 + 审批 + 差异任务 ≥3 组 |
| 障碍登记 | C102-1~5/C103-1~7/C107-2 | SPORT-INT 追加本期障碍（含 wiki 启用、模块树直建、样本采集、执行回填等） |
| 证据 | 部分 | 生产执行 JSON + 截图 + 识图输出 + 差异任务结果落盘 work-logs/evidence/batch-110/ |

## 3. 用户故事 + 验收标准

- As a **承接负责人**, I want 体育平台全部功能模块（用户端/运营后台/konfi）在功能地图与知识中心中闭环，
  so that 后续接口自动化与 UI 自动化有统一的业务事实源。
  - Given 需求文档与生产页面已全量对照，When 查询功能地图 v2 与知识中心，Then 每模块含作用、后台入口、konfi 关联与差异标注。
- As a **自动化测试工程师**, I want 功能用例标注 P0 优先级，so that UI 自动化以 P0 为基线。
  - Given P0 用例已标识，When 按用例映射 UI spec，Then 生产只读执行 ≥8 条并回填结果与截图。
- As a **接口测试工程师**, I want 接口用例以生产真实请求参数为基线、以响应结构做断言，so that 接口自动化贴近生产。
  - Given ≥20 核心接口真实样本，When 生成并执行接口用例，Then 请求参数/断言/实际响应三栏可见且断言命中真实响应结构。
- As a **平台使用者**, I want RAG 与 Wiki 知识库承载需求版本化（13.0/14.0/14.1.0/8.2.0/更新日志），
  so that 后续不同版本迭代差异可对比、可追踪。
  - Given 需求文档已入 RAG 与 Wiki，When 发起差异对比任务，Then 输出版本/模块差异项并可评审。
- As a **平台使用者**, I want 使用少/有障碍的功能被登记，so that 平台逐批迭代改进。
  - Given 本期执行中发现障碍，When 复盘，Then 全部登记至改进任务backlog（SPORT-INT）与 C 条件。

## 4. 技术考量

- 复用 `scripts/sports/*`（import-sports-requirements / ai-generate-sync / knowledge-sync / walkthrough / generate-interface-cases），
  生产执行沿用「生产 API + 直连生产库同步」模式（batch-102/103 已验证，凭证 sportsadmin + production.env DATABASE_URL，不回显入库）。
- 生产页面勘察与 XHR 捕获：扩展 `walkthrough-sports-production.mjs`（全路由发现 + 请求/响应捕获 + 截图）；
  Playwright 使用本机全局安装（C:/Users/26029/AppData/Roaming/npm/node_modules/playwright）。
- 识图走查：生产截图 → vision 视觉模型描述（vision skill，qwen-vl），输出页面功能与「需求 vs 生产」差异 JSON。
- 接口用例：以 `tests/test-case-standards/API接口测试方案.md` + `接口测试规范.md` + `接口测试考虑点【辅助作用】.md` 为规范
  （batch-107 已固化到 ai_service 提示词与生成器），扩展 `TARGETS` 至 ≥20 接口；
  生成器 `generate_cases_from_real_sample` 以真实样本字段为字段来源；响应断言含 envelope/data 结构与关键字段。
- 接口执行：以生产 API 真实调用回填 `last_response_json/last_run_status`（平台已有字段，batch-103 落地）。
- Wiki 基线：新增需求模块树直建脚本（由需求文档提取结果构建 ReleaseBundle + RequirementModule 树），
  走既有 `/wiki/sync/bundle/{id}` → `/wiki/ingest-jobs` → `/wiki/pages/{id}/approve` → `/wiki/diff/tasks` 链路；
  生产需 Railway 变量 `WIKI_ENABLED=true`、`WIKI_DIFF_ENABLED=true`、`WIKI_AUTO_INGEST_ENABLED=true`
  （安全默认 OFF，batch-109 模式：用户手动配置 Railway 或登记为 C 条件）。
- UI 自动化：生产只读 Playwright spec 扩展（`backend/tests/playwright/specs/production-*.spec.ts` 模式），
  P0 用例映射表 + 只读请求守卫（guardProductionRequests，禁止写请求）。
- 障碍登记：`docs/改进任务backlog.md` Epic SPORT-INT 追加 + `C-CONDITIONS.md` C110 条件。

## 5. 范围

**纳入**：生产全路由勘察与识图走查、功能地图 v2、功能用例补齐与 P0 标识、接口真实样本批量采集、
接口用例扩展与执行回填、UI 自动化 P0 映射与生产执行、RAG 与 Wiki 知识库接入（含模块树直建脚本）、
障碍登记与 C 条件。

**非目标**（见头部）：Test5 内网、运营后台生产账号、AI 异步化改造、差异标注 UI、性能优化、iOS 真机、
平台发布门禁、外部 LLM-Wiki、match replays URL、运营后台生产勘察。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 生产用户端全路由勘察 + XHR 捕获 + 截图 + 识图走查 | JSON+截图+识图差异输出落盘 |
| S2 | 功能地图 v2 + 功能用例补齐 + P0 标识 | 地图文档 + 用例优先级落库 |
| S3 | 接口真实样本 ≥20 + 接口用例生成 + 核心接口执行回填 | 用例三栏可见 + 证据 JSON |
| S4 | RAG 入库 + Wiki 基线（模块树/同步/编译/审批/差异） | sources/raw sources/pages/diff 证据 |
| S5 | UI 自动化 P0 映射 + 生产只读执行 | spec + 结果 + 截图 |
| S6 | 障碍登记 + QA + Leader + 一次总确认 → PR | 全部门工件 + 证据完备 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线与批次工件（本 PRD）
- `playwright-cli` / `playwright-skill` → 生产页面勘察、XHR 捕获、UI 自动化执行
- `vision` → 生产截图识图走查（页面功能/差异描述）
- `test-case-design` → 功能用例与接口用例规范核对
- `cameltv-api-test` → 接口测试执行与断言核对
- `cameltv-bug-guard` → 脚本/代码编写前避坑
