# Batch 110 — PM Plan（体育平台第一期收口）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: PRD §1（全模块覆盖 / P0 用例 / 接口真实样本 ≥20 + 执行回填 / UI 自动化基于 P0 /
RAG+Wiki 版本化 / 障碍登记）
**目标时间**: 2 个开发日（切片 30–60 分钟粒度，生产执行依赖 sportsadmin 凭证与生产 DB URL）
**执行器**: codex（用户确认）；worktree: `F:\CamelTv-worktrees\codex-batch-110-sports-phase1-closeout`

## 开发任务

### [ ] Task 1: 批次工件 + 看板 + 障碍快照
**描述**: 产出 PRD/PM/Design 三件套、DEV 看板；读取 C-CONDITIONS Open 条件并快照本期纳入/豁免。
**验收标准**: 三工件+看板存在；PRD 含 mode: full 与非目标。
**涉及文件**: `test-platform-v2/work-logs/batch-110-*-{prd-summary,pm-plan,design-spec}.md`、`kanbans/DEV-batch-110-sports-phase1-closeout.md`

### [ ] Task 2: 生产用户端全路由勘察 + XHR 捕获（脚本扩展）
**描述**: 扩展 `scripts/sports/walkthrough-sports-production.mjs`：自动发现首页全部导航/链接 → 遍历核心路由
（含 /my 全子页、登录、搜索、联赛/球队/球员、回放、世界杯、赛事详情、直播间、资讯详情），
同时用 Playwright route/request 监听捕获 XHR 请求与响应（≥20 核心接口真实样本）。
**验收标准**: 生产执行输出 pages.json（≥25 路由）+ screenshots/ + xhr-samples.json（≥20 接口，含请求体/响应体）。
**涉及文件**: `scripts/sports/walkthrough-sports-production.mjs`、`scripts/sports/capture-xhr-samples.mjs`（新增）
**参考**: PRD §4、batch-102 walkthrough 脚本

### [ ] Task 3: 识图走查（vision）
**描述**: 将 Task 2 截图分批交给 vision 模型（vision skill）输出页面功能描述与「需求 vs 生产」差异 JSON；
合并为 `vision-walkthrough.json`。
**验收标准**: 主要页面均有识图描述；差异项带证据（截图路径）。
**涉及文件**: `test-platform-v2/work-logs/evidence/batch-110/vision-walkthrough.json`

### [ ] Task 4: 功能地图 v2
**描述**: 在 `docs/体育平台-功能模块地图.md` 上补全：用户端全模块（登录注册/我的全子页/支付/消息等）、
运营后台全模块（消息/球队联赛/用户管理/系统管理/财务/赛事预测等）、konfi 关联更新、
需求 vs 生产差异标注（含识图结论）。
**验收标准**: 地图文档覆盖用户端/运营后台全部功能模块，含每模块作用、后台入口、konfi 关联、差异标注。
**涉及文件**: `test-platform-v2/docs/体育平台-功能模块地图.md`

### [ ] Task 5: 功能用例补齐 + P0 标识
**描述**: 对待补模块（消息/球队联赛/用户管理/系统管理及新增差异模块）用本地 ai_service 生成补齐用例并导入；
按关键用户路径（登录注册/首页/赛事详情/直播/资讯/搜索/我的资产/充值支付等）将核心用例 priority 标为 P0。
**验收标准**: 用例数补齐（记录补量）；P0 ≥30 条落库可查。
**涉及文件**: `scripts/sports/ai-generate-sync.py`（扩展）、`scripts/sports/mark-p0-cases.py`（新增）
**参考**: PRD §2 指标、batch-103 local-ai 通道

### [ ] Task 6: 接口真实样本批量采集 + 接口用例生成
**描述**: 由 Task 2 的 xhr-samples 提炼 ≥20 核心接口真实请求样本，扩展 `scripts/sports/generate-interface-cases.py`
的 TARGETS；以真实样本字段为来源调用 `generate_cases_from_real_sample`/`generate_cases_from_endpoint` 生成字段级用例
（含响应结构/关键字段断言）并直连生产库落库。
**验收标准**: ≥20 接口生成用例；每条含 api_body/api_assertions/case_design_method/positive_negative。
**涉及文件**: `scripts/sports/generate-interface-cases.py`、证据 JSON
**参考**: C103-3/4/5、API接口测试方案.md

### [ ] Task 7: 接口测试执行回填
**描述**: 对核心接口（≥10）以真实请求实跑生产 API，将响应回填 last_response_json/last_run_status；
断言按响应结构（envelope/data/records 长度/关键字段非空）。
**验收标准**: 用例详情「请求结果」可见；执行证据 JSON + 断言通过清单。
**涉及文件**: `scripts/sports/execute-interface-cases.py`（新增）
**参考**: C103-2/7

### [ ] Task 8: RAG 知识中心入库
**描述**: 将 4 份需求文档全文 + 功能地图 + 接口规范导入知识中心（标准 `/knowledge/capture`，batch-108 已修复；
若仍受阻则按知识同步脚本直连语义补入并登记）；扩展图谱实体/关系（新增模块）。
**验收标准**: sources 列表可见新增源；图谱实体/关系增长有证据。
**涉及文件**: `scripts/sports/knowledge-sync.py`（扩展）

### [ ] Task 9: Wiki 基线（需求模块树直建 + 同步 + 编译 + 审批 + 差异）
**描述**: 新增 `scripts/sports/build-wiki-baseline.py`：由需求文档提取结果构建 ReleaseBundle + RequirementModule 树
（平台 APP/PC/WEB/ADMIN → 模块 → 页面 → 功能点），走 `/wiki/sync/bundle/{id}` → `/wiki/ingest-jobs` →
`/wiki/pages/{id}/approve` → `/wiki/diff/tasks`（RAG vs Wiki、13.0 vs 14.0 等 ≥3 组）。
生产启用 `WIKI_ENABLED=true`（Railway 变量，用户配置或登记 C 条件）。
**验收标准**: raw sources/页面/差异任务证据；wiki diff 输出差异项可评审。
**涉及文件**: `scripts/sports/build-wiki-baseline.py`（新增）、`test-platform-v2/work-logs/evidence/batch-110/wiki-*`
**参考**: wiki.py sync/ingest/diff 路由、C102-3/C27-C4

### [ ] Task 10: UI 自动化（P0 用例 → 生产只读执行）
**描述**: 产出「P0 功能用例 → UI spec」映射表；扩展生产只读 Playwright spec（导航/首页/赛事详情/资讯/搜索/我的/回放/世界杯），
含 guardProductionRequests 只读守卫；生产执行并截图。
**验收标准**: ≥8 条 UI 检查执行通过 + 截图 + 控制台无错误；写请求被守卫拦截。
**涉及文件**: `test-platform-v2/backend/tests/playwright/specs/production-p0-*.spec.ts`（新增）、映射表文档

### [ ] Task 11: 障碍登记 + QA + Leader + 一次总确认
**描述**: 更新 `docs/改进任务backlog.md` Epic SPORT-INT（含 wiki 启用/模块树直建/样本采集/执行回填等新障碍）、
C-CONDITIONS.md C110 条件；写 QA 报告（硬门禁+生产证据）、Leader 判决（含流程回写+复盘卡）；
展示变更摘要并完成一次总确认（推送+Draft PR+checks 合入）。
**验收标准**: audit-cconditions 0 硬错；工件齐全；总确认授权记录。

## 质量要求

- [ ] 脚本 py_compile / node --check 通过
- [ ] 相关 pytest/vitest 按变更域执行并记录退出码（C78-1）
- [ ] ruff F821、前端 typecheck/build（若改前端）
- [ ] 无 console.log/print/breakpoint/debugger 调试残留（脚本运行输出除外，登记豁免）
- [ ] 无硬编码密钥；凭证仅经环境变量/参数注入
- [ ] 生产只读原则：生产请求仅 GET/HEAD + 已授权只读会话；写操作仅限平台自身的已验证数据通道
- [ ] 双 404 约定（C86-1）适用于新增断言
