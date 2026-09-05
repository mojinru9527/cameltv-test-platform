---
title: "Batch 230 — 生产复测缺陷修复 PRD"
owner: "qa-team"
date: "2026-09-05"
status: "Approved"
mode: "full"
batch: "batch-230-prod-retest-defects"
branch: "feature/batch-230-prod-retest-defects"
executor: "claude"
workflow: "agent-team"
defects: ["DEF-20260905-001", "DEF-20260905-002", "DEF-20260905-003", "DEF-20260905-004", "DEF-20260905-005", "DEF-20260905-006", "DEF-20260905-007", "DEF-20260905-009"]
evidence: "work-logs/evidence/sports-e2e-20260904/复测结论-20260905.md"
tags: ["batch-230", "defect-fix", "aitde", "version-task", "production-retest"]
---

# Batch 230 — PRD Summary
> **Product (🟦)** | Date: 2026-09-05 | Status: Approved

## 0. 批次模式判定

**完整批次**（`mode: full`）。判定依据：本批引入新行为与新接口字段，不属纯修复。

| 触发项 | 说明 |
|---|---|
| 新接口字段 | `GET /api/v2/missions/{id}/contract` 需新增 `snapshot` 字段（暴露既有 `snapshot_json` 解析结果），属 API 契约变更 |
| 新前端视图 | `/version-tasks` 需新增任务列表视图（当前该路由只有建任务向导，列表视图在全仓不存在） |
| 新校验行为 | 契约冻结需新增「快照非空」前置校验；版本任务运行需新增「无可执行条目」业务错误 |

故六件工件（PRD + PM + Design + Dev + QA + Leader）全部产出，不适用轻量豁免。

## 1. 问题陈述

2026-09-05 对生产 `https://swiftbugs.cn` 做了一轮全前端黑盒复测（纯浏览器真实用户操作，不使用接口模拟），复测 2026-09-04 提交的 15 条缺陷，并新发现 9 条。新发现中 8 条经代码侧交叉验证确认为真实缺陷，本批处理这 8 条。

**为什么用户关心**：这 8 条集中在平台两条主干上——AITDE Mission 主链（资料→范围→契约→场景→执行→验收）与版本验收链路（建任务→审方案→执行→放行）。复测已证明 Mission 主链在前一批修复后**首次越过第 2 阶段**，但随即在第 3 阶段撞上「契约是空壳」；版本验收链路则在第 1 步之后就断裂（任务创建后界面上再也找不到）。也就是说，平台刚刚打通的进展立刻被下一批缺陷挡住，用户拿到的是「能点但拿不到结果」的半成品体验。

**证据**（均为生产实测，非推断）：

| 缺陷 | 级别 | 生产实测证据 | 代码侧根因（已定位） |
|---|---|---|---|
| DEF-20260905-001 | P1 | `GET /api/v2/missions/37/contract` 仅返回 `{contract_id,name,version_no,version{...content_hash}}`，无任何条目；页面可对该空壳点「冻结契约」 | 序列化丢字段：`backend/app/modules/aitde/contract/service.py:230-241` 的 `_version_to_dict` 不输出 `snapshot_json`。内容其实已生成——`intelligence/provider.py:210-238` 的确定性 `build_contract` 会按已批准范围项产出 `ContractRule` 列表并存入 `TestContractVersion.snapshot_json`；`content_hash` 就是整个快照的 sha256 前 32 位，非空哈希反证内容非空。`contract/schemas.py:46-54` 的 `ContractVersionRead` 已声明 `snapshot_json` 但从未被使用；前端 `frontend/src/api/contract.ts:3-24` 已定义 `ContractSnapshot/ContractRule/ContractOutcome` 类型但从未被消费 |
| DEF-20260905-002 | P1 | `POST /api/v1/version-tasks` 返回 200 且 `id=4`，但 `/version-tasks` 刷新后仍只有建任务表单；侧边栏「版本验收任务」为 `<a href=null role=null>`，点击 URL 不变；只有手打 `/version-tasks/4` 能打开详情 | 列表视图**全仓不存在**：`frontend/src/pages/version-tasks/index.tsx:21-208` 只渲染三步向导，状态全在 `useState`，刷新即丢，且从不拉取已有任务。API 侧已就绪——`frontend/src/api/versionTask.ts:81-89` 有 `listVersionTasks`，`backend/app/api/v1/version_task.py:68-81` 有 `list_tasks` 返回 `Page[VersionTaskListItem]`，但 `listVersionTasks` **零消费者**。死链根因另见 `frontend/src/layouts/MainNavRows.tsx:61-71`：分组子项用 `SidebarMenuSubButton` 但未传 `asChild`/`href`，而 `components/ui/sidebar.tsx:649-676` 的 `const Comp = asChild ? Slot : "a"` 使其降级为无 href 的裸 `<a>`（导航仅靠 `onClick`） |
| DEF-20260905-003 | P1 | `POST /api/v1/version-tasks/4/run` 返回 `status:"blocked", total:0, blocked:0, evidence:[], failures:[]`，耗时 18ms；界面显示「状态 已执行 / 覆盖 0/0 / 阻塞 0」，无 toast 无原因 | 后端 `backend/app/services/version_task_service.py:344` 只把 `status in ("adopted","modified")` 的方案条目转为校验项，draft 任务无方案条目 → `total=0`；`:396-397` 据此置 `run_status="blocked"`，但逐条 `blocked` 计数器（`:375`）只在 `not_run` 时自增，故出现 `status=blocked` 而 `blocked=0`；`:424` **无条件** `task.status = "executed"`。前端 `[taskId].tsx:7-17` 的 `TASK_STATUS_LABEL` 映射的是任务状态（含 `executed:'已执行'`），运行态 `blocked` **从未被渲染**；`handleRun`（`:58-69`）恒发 `toast.success('运行完成：0 通过 / 0 失败')`，无 blocked 分支。后端也没有承载原因的字段：`schemas/version_task.py:199-214` 的 `VersionTaskRunOut` 无顶层 reason |
| DEF-20260905-004 | P2 | `POST /api/v1/ai-config/providers/discover-models` 返回 `{"code":0,"msg":"ok","data":{"ok":false,"error":"请先填写 API Key 再获取模型列表"}}`，前端弹成功 toast「已拉取厂商全量模型（共 5 个）」，模型清单实际未变 | `backend/app/api/v1/ai_config.py:106-116` 把业务失败包进 `R.ok(...)`（200 信封）；`frontend/src/api/aiConfig.ts:75-79` 的 `discoverAiModels` 返回类型只声明 `{models:string[]}`，**未声明 `ok`/`error`**（对比同文件 `:57-69` 的 `testAiProviderConnection` 声明完整）；`frontend/src/pages/ai-config/index.tsx:242-270` 的 `handleDiscoverModels` 在 `:254` 用 `res?.models ?? []` 合并，失败时得到原有 5 个模板模型，直接走到 `:263` 的 `toast.success`，全程未检查 `ok` |
| DEF-20260905-005 | P2 | 列表含 15 条 `DEF-20260904-xxx`，搜索「DEF-20260904」返回 0 条；搜标题关键词「篮球」正常返回 11 条。另一项目同样复现 | `backend/app/services/defect_service.py:87-88` 仅 `Defect.title.contains(keyword)`，从不搜 `defect_id`（列定义 `backend/app/models/defect.py:18`，`String(50)`，由 `defect_service.py:33-42` 的 `_generate_defect_id()` 生成）。前端只有一个 `keyword` 参数（`frontend/src/pages/defect/index.tsx:26-40`、`DefectFilterBar.tsx:69-72`，placeholder 自称「搜索缺陷标题」），后端 `api/v1/defect.py:64-85` 也只有 `keyword`，无独立编号参数 |
| DEF-20260905-006 | P2 | 批准 3 条范围项后，审计日志 `scope:analyze` 1 条与 `scope:review` 3 条的操作人**完全为空**；同一会话的 `defect:create` 正常显示当前管理员登录名 | `backend/app/modules/aitde/scope/service.py:136-157` 的 `_audit` 在 `:150` **硬编码 `username=""`**（`ip` 同样为空）。对比 `backend/app/api/v1/defect.py:21-33` 的 `_audit` 接收 `Request`+`CurrentUser` 并传 `username=cu.user.username`。API 层 `backend/app/api/v2/mission_scope.py:31-32,64-65` 只向下传 `current.user.id`，username 从未进入服务层。非后台任务路径，纯粹是漏传参数 |
| DEF-20260905-007 | P3 | Mission 契约页渲染「歧义（Ambiguitity）」 | `frontend/src/pages/missions/contract.tsx:175` 字面量拼写错误（多一个 i）。后端 `/ambiguities`、`scope/ambiguity_*` 拼写正确，纯前端 |
| DEF-20260905-009 | P3 | 访问不存在的 `/defects`、`/environments`，页面先渲染「V4.0：旧版入口收敛中／此页面属于历史入口…」横幅，其下才是 404 空态——一个根本不存在的页面被告知「这是正在收敛的历史入口」 | `frontend/src/components/legacy/LegacyNoticeBanner.tsx:8-26` 用硬编码 `LEGACY_PREFIXES`（含 `'/defect'`、`'/environment'`）做 `pathname.startsWith(p)` 无边界前缀匹配，故 `/defects`.startsWith(`/defect`) 为真。横幅在 `frontend/src/layouts/MainLayout.tsx:460` 渲染于 `<Outlet/>` 之上，而 404 路由 `{path:'*',element:<NotFound/>}`（`router/index.tsx:503`）是 MainLayout 的**子路由**，因此未知路径也在 MainLayout 内渲染 → 横幅必然出现在 404 之上。真实路由是单数（`router/index.tsx:256,257,262`）。`frontend/src/pages/NotFound.tsx:5-16` 为静态 404，**不存在**任何「相近模块建议」机制 |

**范围决议**：本批 8 条全部为「已定位根因、修法明确」的缺陷，不含探索性重构。

### 1.1 主动撤回的一条（不计入本批）

**DEF-20260905-008（生成契约无成功提示）为测试方误报，已在生产平台走「评论 + 状态流转 → 已拒绝」正式撤回**，附撤回理由与代码侧交叉验证。

复测时用 `MutationObserver` 监听 sonner toast 重新验证：点击「重新生成」后确实弹出「契约已生成」。原报告错误在于点击后等待过久才读取 toast 列表，而 sonner 默认约 4 秒自动消失，读取时提示已关闭。代码侧 `frontend/src/pages/missions/contract.tsx:108-125` 的 `doGenerate` 在 `:113` 已有 `toast.success('契约已生成')`，与范围页 `scope.tsx:88` 的「已批准」为同一模式。

**流程教训（供 Leader 流程回写）**：黑盒缺陷录入前，对「无提示／无反馈」类结论必须用事件监听而非事后快照取证。本批把该要求写入 QA 门禁。

## 2. 成功指标

| 指标 | 基线（2026-09-05 生产实测） | 目标 | 测量窗口 |
|---|---|---|---|
| Mission 契约阶段可评审性 | `GET .../contract` 返回 0 个条目，页面 0 条规则可见 | 返回并渲染 ≥1 条 `ContractRule`（等于已批准 INCLUDE 范围项数）；空快照时禁止冻结并给出原因 | 本批 QA + 生产复测 |
| 版本任务可达性 | 创建后 UI 无任何入口，只能手打 `/version-tasks/{id}` | `/version-tasks` 列出本项目全部任务并可点进详情；侧边栏「版本验收任务」为真实 `href`，可键盘聚焦 | 本批 QA |
| 版本任务空跑可见性 | `status=blocked/total=0` 被显示为「已执行 / 阻塞 0」，无原因 | `total=0` 时不再记为已执行；界面显示阻塞态与人话原因 | 本批 QA |
| 假成功提示 | 「自动发现」失败仍弹成功 toast | `ok=false` 时弹 `error` 原文的错误 toast，模型清单不变 | 本批 QA |
| 缺陷可检索性 | 按编号搜 0 命中 | 按编号（含前缀）搜命中；按标题搜不回归 | 本批 QA |
| 评审决策可追责 | `scope:analyze`/`scope:review` 操作人为空 | 两类事件操作人 = 登录名，与 `defect:create` 同口径 | 本批 QA |
| 文案与横幅正确性 | 「Ambiguitity」拼写错误；404 页叠加收敛横幅 | 拼写为 Ambiguity；404 页不渲染收敛横幅 | 本批 QA |
| 本批回归 | — | 前后端硬门禁全绿，无新增失败 | 本批 QA |

## 3. 非目标（本次不做）

| 排除项 | 原因 |
|---|---|
| DEF-20260904 系列复测确认未修复的 9 条（-001/-003/-007/-008/-009/-012/-013/-014/-015） | 用户已明确决定拆两批、先修新录 9 条。其中 -012（Source 定长切块）需重构解析策略、-008（编号加项目维度）可能涉及 Schema 变更，体量与风险都应独立成批。**但**：本批修 DEF-20260905-002 时会顺带修好侧边栏 `href` 缺失，这与 DEF-20260904-001 同源；两批需在 PM 计划中显式标注交界，避免重复修或漏修 |
| 契约内容的**质量**提升（规则是否覆盖全部需求点、是否含字段级断言） | 本批只解决「已生成的内容拿不到、看不见」。内容质量依赖 AI Key（项目级隔离，当前项目未配置），属待提供清单 A1，非代码可解 |
| 新增 `ContractItem` 数据表 | 代码勘察确认现设计就是把条目存进 `TestContractVersion.snapshot_json`，`content_hash` 即快照哈希。这是既有设计意图，不是缺失的表；改表结构属过度设计 |
| 版本任务运行时的真实执行能力（生成校验项、跑通断言） | 本批只修「空跑被记为已执行且无原因」。让 draft 任务真的产出校验项需要先有已采纳的验收方案，属 B7/B8（batch-217/218）既有链路，不在本批 |
| 404 页「相近模块建议」 | 该机制全仓不存在（`NotFound.tsx` 为静态组件，无建议逻辑；`CommandPalette.tsx` 有关键词索引但未接入）。新建路由建议引擎属新功能，超出缺陷修复范围，留待 DEF-20260904-004 批次 |
| 后端 `{"ok": false}` 装进 `R.ok(...)` 200 信封这一系统性模式 | 勘察确认该模式在 `ffmpeg_service`、`test_plan_service`、`wiki/external_llm_wiki`、`lanhu_evidence_jobs`、`aitde/cleanup_service` 等处广泛存在，但**假成功 toast 目前只有 `discoverAiModels` 一处**（其余消费者 `testAiProviderConnection`、`lanhuRelogin`、`testDataSourceConnection` 都正确检查了 `ok`）。本批只修该处并加守卫测试；统一信封语义属架构级变更，另立批次 |
| 生产部署与发布 | 按 AGENTS.md §2.6，合入主干 ≠ 发布。本批只负责代码进 main，发布走 release 火车 |

## 4. 用户故事 + 验收标准

### US-1 契约可评审（DEF-20260905-001，P1）

As a **QA 负责人**, I want **在 Mission 契约页看到生成出来的契约条目**, so that **我能判断契约是否值得冻结，而不是对一个看不见的哈希做决策**。

- 验收：Given Mission 已完成范围评审（3 项均 APPROVED+INCLUDE）且已生成契约 v1 / When 打开契约 Tab / Then 页面渲染出规则列表，条数 = 已批准 INCLUDE 范围项数（本例 3），每条显示 `rule_key`、标题、陈述与风险等级；`GET /api/v2/missions/{id}/contract` 响应含解析后的 `snapshot`。
- 验收（反例）：Given 某契约版本的 `snapshot_json` 为空或 `rules` 为空数组 / When 点「冻结契约」 / Then 拒绝冻结并给出人话原因（如「契约无有效条目，不可冻结」），不得静默成功。
- 验收（反例）：Given 范围未 100% 评审 / When 生成契约 / Then 维持既有 `_freeze_precondition` 行为不变（本批不放宽任何前置校验）。

### US-2 版本任务可达（DEF-20260905-002，P1）

As a **QA**, I want **在 /version-tasks 看到我创建过的所有版本验收任务**, so that **建完任务后能继续走审方案与放行，而不是任务凭空消失**。

- 验收：Given 本项目已有 ≥1 个版本任务 / When 访问 `/version-tasks` / Then 显示任务列表（至少含标题、版本号、状态、创建时间），每行可点进 `/version-tasks/{id}`；建任务向导仍可用（列表与向导同页分区或分 Tab，由 Design 定）。
- 验收：Given 本项目 0 个任务 / When 访问 `/version-tasks` / Then 显示空态而非空白，且建任务入口可见。
- 验收：Given 侧边栏展开「版本验收」分组 / When 检查「版本验收任务」「版本发布包」「智能测试任务」「报告中心」「缺陷管理」5 项 / Then 均为带真实 `href` 的锚点，`Tab` 键可聚焦，回车可导航，右键可复制链接。
- 验收（刷新持久）：Given 刚创建任务成功 / When 刷新页面 / Then 新任务出现在列表中（不得依赖内存态）。

### US-3 空跑不再伪装成已执行（DEF-20260905-003，P1）

As a **放行决策人**, I want **一次什么都没跑的运行明确告诉我它没跑以及为什么**, so that **我不会把 0 校验当成「已验证」而误放行**。

- 验收：Given 任务处于 draft 且无已采纳方案条目 / When 点「一键运行」 / Then **不得**把任务置为 `executed`；界面显示阻塞态与人话原因（如「无可执行条目：请先在建任务页生成并采纳验收方案」）。
- 验收：Given 运行返回 `status="blocked"` / When 查看任务详情 / Then 运行态标签显示「已阻塞」（而非「已执行」），且不弹成功 toast。
- 验收（一致性）：Given 任意运行结果 / When 对比接口 `status` 与界面标签 / Then 二者语义一致，不得出现接口 blocked 而界面已执行。
- 验收（反例）：Given 任务有 ≥1 条已采纳方案条目 / When 点「一键运行」 / Then 正常执行并置 `executed`，既有通过路径不回归。

### US-4 失败不得报成功（DEF-20260905-004，P2）

As a **平台使用者**, I want **「自动发现」失败时看到真实错误**, so that **我不会以为模型清单已更新而在错误前提下继续配置**。

- 验收：Given 编辑提供方时 Key 留空 / When 点「自动发现」 / Then 弹错误 toast 显示后端 `error` 原文（「请先填写 API Key 再获取模型列表」），模型清单保持不变，**不得**出现「已拉取厂商全量模型」字样。
- 验收：Given 填入有效 Key / When 点「自动发现」成功 / Then 仍弹成功 toast 且清单更新为接口返回值（成功路径不回归）。
- 验收（类型守卫）：`discoverAiModels` 的 TS 返回类型必须声明 `ok`/`error`，使漏检 `ok` 在 `npm run typecheck` 阶段即暴露。

### US-5 缺陷可按编号定位（DEF-20260905-005，P2）

As a **跨团队协作的 QA**, I want **用缺陷编号直接搜到缺陷**, so that **拿到一个编号就能定位，不必翻页肉眼找**。

- 验收：Given 列表含 `DEF-20260904-001..015` / When 搜索「DEF-20260904」 / Then 返回全部 15 条；搜「DEF-20260904-010」返回该 1 条。
- 验收（不回归）：Given 同上 / When 搜索标题关键词 / Then 命中集合与修复前一致。
- 验收：搜索框 placeholder 与实际能力一致（不得继续自称「搜索缺陷标题」）。
- 验收（边界）：搜索仍受项目隔离约束，不得因新增 OR 条件而跨项目泄漏。

### US-6 评审决策可追责（DEF-20260905-006，P2）

As a **审计者**, I want **范围评审动作记录到操作人**, so that **能回答「这条范围是谁批准的」**。

- 验收：Given 登录用户批准/拒绝范围项 / When 查看审计日志 / Then `scope:review` 行操作人 = 该用户登录名，与 `defect:create` 同口径。
- 验收：Given 触发范围分析 / When 查看审计日志 / Then `scope:analyze` 行操作人非空。
- 验收（同类排查）：AITDE 其余服务层若存在同样的 `username=""` 硬编码，一并修正或在 QA 报告中列出并说明豁免理由。

### US-7 术语与横幅正确（DEF-20260905-007 P3、DEF-20260905-009 P3）

As a **用户**, I want **界面术语拼写正确、且不存在的功能不要声称正在收敛**, so that **我能信任界面传达的信息**。

- 验收：Given 打开 Mission 契约页 / Then 标签为「歧义（Ambiguity）」。
- 验收：Given 访问 `/defects`、`/environments` 等未注册路由 / Then 只渲染 404 空态，**不**渲染 V4.0 收敛横幅。
- 验收（不回归）：Given 访问真实历史入口 `/defect`、`/environment` 及其子路径（如 `/defect/123`） / Then 收敛横幅照常渲染。
- 验收（健壮性）：横幅显隐不得依赖易碰撞的裸前缀匹配；需按路径段边界判断或按「命中的是否为 404 路由」判断，避免未来新增前缀再次误命中。

## 5. 技术考量

**依赖与既有资产（可复用，不必新造）**：
- 契约内容已存在于 `snapshot_json`，`ContractVersionRead`（`contract/schemas.py:46-54`）与前端类型（`api/contract.ts:3-24`）均已定义但闲置 → US-1 主要是「接通」而非「新建」。
- 版本任务列表 API 双端均已存在（`list_tasks` + `listVersionTasks`），仅缺 UI 消费者 → US-2 后端零改动。
- 版本任务状态机已允许 `executing→blocked`（`version_task_service.py:29`）→ US-3 无需扩状态机。
- 审计写入器 `write_audit`（`services/audit_service.py:12-23`）本就接收 `username` → US-6 是补参数传递链，不改写入器。

**已知风险**：
1. **US-1 契约响应新增 `snapshot` 属 API 契约变更**，须同步 OpenAPI schema（AGENTS.md §3.2）。需确认是否有其他消费者依赖当前精简响应体。
2. **US-3 改 `task.status` 赋值条件**触及版本放行主链路（B8/B9，batch-218/219 已交付）。放行证据包基于 `coverage`/`verdict` 生成（C218-1 已关闭），若任务不再轻易进入 `executed`，须验证放行页与证据包不被连带打断 → QA 必须覆盖放行路径回归。
3. **US-2 侧边栏改 `asChild` + `Link`** 影响全部 5 个分组子项的导航行为，属高扇出改动。`nav-config.ts:25-30` 的 `path` 值本身正确（`backend/app/seed.py:16-72` 播种，`seed.py:337-351` 会对账陈旧 path），因此风险在渲染层而非数据层；仍需回归全部子项点击。
4. **US-5 新增 OR 条件**若写错可能绕过项目隔离过滤 → 必须验证 `project_id` 约束仍在 OR 之外（括号优先级）。
5. **与 batch-231 的交界**：DEF-20260904-001（侧边栏死链）与本批 US-2 的 href 修复同源。本批修 href，下一批不得重复修；PM 计划须显式标注，Leader 须在 C 条件中记录该交界。

**与既有 C 条件的关系**：
- **C225-1（Open，P1）**要求对 B1-B15 做最终验收黑盒走查（登录→我的待办→版本验收→执行→缺陷→放行→知识复用→资产库可达）。本轮生产复测正是该走查的一次执行，DEF-20260905-002/-003 就是走查在「版本验收→执行→放行」段发现的阻断。本批修复后，C225-1 的该段证据可复用，但 C225-1 整体（含交付文档）仍不满足解除条件 → 本批**不关闭** C225-1，仅在其下补充证据引用。
- **C227-1（Open，P1）**为 batch-227 的合入门禁，与本批无直接冲突，但本批 Leader 判决须遵循同一门禁形态（required checks 全绿 + 最终审计）。
- **C216-1 / C218-1（均 Closed）**是本批改动区域的既有约束：不得另造任务容器、放行必须基于 VersionTask 的 `verdict`/`coverage`。US-2 必须复用 `listVersionTasks` 而非新建列表接口；US-3 不得新造放行态。

**待解决问题**：
- 生产是否运行最新前端构建尚未核实。DEF-20260905-008 的误报提醒：生产行为与 main 代码可能不同步。QA 阶段须先确认「本地 main 能复现该缺陷」，凡本地无法复现的一律标注并回报，不得凭生产观察直接改代码。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|---|---|---|
| 本地验证 | Dev + QA | 前端 `npm ci && npm run typecheck && npm run build` 全绿；后端 app 导入、`ruff check app --select F821`、Alembic 单头与 revision 长度测试全绿；受影响模块 Pytest/Vitest 通过并记录退出码 |
| PR 门禁 | CI | Draft PR required checks（按变更范围分类：本批同时触及前后端 → 双端 required 均须运行）全绿；`audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor claude -RequireSuccessfulChecks` 通过 |
| 合入 main | Leader | 用户一次总确认（推送+PR+合入）+ QA PASS + Leader APPROVED |
| 发布 | 运维 | 按 AGENTS.md §2.6 走 release 火车，本批不单独发布 |
| 生产复测 | QA | 发布后用与 2026-09-05 完全相同的前端黑盒手法逐条复测 8 条，结论回写 `work-logs/evidence/` |

## 7. 技能使用

| 技能 | 产出 / 结论 |
|---|---|
| `cameltv-agent-team` | 驱动本批六部门流水线；据其「批次模式」判定为完整批次；据其 Git 门禁创建独立 worktree（`claude-batch-230-prod-retest-defects`，端口 5231/8231，`verify-ai-worktree.ps1` 通过，DirtyFiles=0） |
| `playwright-cli` | 生产黑盒取证与 DEF-20260905-008 误报的 `MutationObserver` 复验；撤回操作（评论 + 状态流转至已拒绝）亦经其完成 |
| Explore 子代理（3 路并行） | 定位全部 8 条缺陷的代码根因与「文件:行号」锚点；确认 `ContractItem` 表不存在、版本任务列表 API 双端已存在但零消费者、`NotFound` 无建议机制、假成功 toast 仅 `discoverAiModels` 一处 |

> 说明：技能调用记录不构成测试证据（SKILL.md 第 4/5 步）。`cameltv-bug-guard` 与 `cameltv-ui-conventions` 按流程在 Dev / Design 阶段调用，结论写入对应工件。
