---
title: "Batch 230 — 生产复测缺陷修复 PM Plan"
owner: "qa-team"
date: "2026-09-05"
status: "Approved"
batch: "batch-230-prod-retest-defects"
prd: "work-logs/batch-230-prod-retest-defects-prd-summary.md"
tags: ["batch-230", "pm-plan"]
---

# Batch 230 — PM Plan
> **PM (🟨)** | Date: 2026-09-05

## 规格摘要

**原始需求**：PRD §4 US-1..US-7，修复 2026-09-05 生产复测确认的 8 条缺陷 DEF-20260905-001..007、-009（-008 已由提交人撤回，不在范围内）。
**目标时间**：单批交付，7 个 Slice，总预估 9.5h。
**批次模式**：完整批次（PRD §0）。

**范围纪律**：以下任务全部可追溯到 PRD 用户故事，**不含 PRD 未写的任何需求**。PRD §3 非目标（契约内容质量、`ContractItem` 建表、404 相近模块建议、后端 `ok:false` 信封统一、真实执行能力）一律不得在本批实现；若开发中发现必须动，先停下回报，不得自行扩范围。

## 切片与依赖

| Slice | 对应 US / 缺陷 | 层 | 依赖 | 预估 |
|---|---|---|---|---|
| S1 | US-1 / DEF-20260905-001 (P1) | 后端 + 前端 | 无 | 2.0h |
| S2 | US-2 / DEF-20260905-002 (P1) | 前端 | 无 | 1.5h |
| S3 | US-3 / DEF-20260905-003 (P1) | 后端 + 前端 | 无（但与 S2 同文件域，S2 先合） | 1.5h |
| S4 | US-4 / DEF-20260905-004 (P2) | 前端 | 无 | 0.75h |
| S5 | US-5 / DEF-20260905-005 (P2) | 后端 + 前端文案 | 无 | 0.75h |
| S6 | US-6 / DEF-20260905-006 (P2) | 后端 | 无 | 1.0h |
| S7 | US-7 / DEF-20260905-007 + -009 (P3) | 前端 | S1（同文件 `missions/contract.tsx`），S1 先做 | 1.0h |

**排序理由**：S1 与 S7 同改 `frontend/src/pages/missions/contract.tsx`，S1 先做以免冲突；S2 与 S3 同属版本任务域但改不同文件（`index.tsx` vs `[taskId].tsx`），S2 先做因 S3 的界面标签依赖列表页可达后才能完整走查。其余无依赖，可并行。

---

## 开发任务

### S1 — 契约快照暴露与渲染（DEF-20260905-001，P1）

#### [ ] Task 1.1 后端：`get_current` 输出解析后的 snapshot
**描述**：`_version_to_dict` 增加 `snapshot` 键，值为 `snapshot_json` 的 `json.loads` 结果（解析失败或为空时给 `None`，不得抛异常打断响应）。不改 `content_hash` 语义，不改 `snapshot_json` 存储格式。
**验收标准**：
- `GET /api/v2/missions/{id}/contract` 响应 `data.version.snapshot.rules` 为数组，长度 = 已批准 INCLUDE 范围项数
- `snapshot_json` 为空/损坏时接口仍 200，`snapshot` 为 `null`
- 既有字段（`id/contract_id/version_no/status/content_hash/created_at/approved_at`）一个不少
**涉及文件**：
- `test-platform-v2/backend/app/modules/aitde/contract/service.py:230-241` — `_version_to_dict` 增加 snapshot 解析
- `test-platform-v2/backend/app/modules/aitde/contract/service.py:123-133` — 确认 `get_current` 透传
**参考**：PRD §1 表格第 1 行 / §5 依赖「`ContractVersionRead`（`contract/schemas.py:46-54`）已声明 `snapshot_json` 但闲置」

#### [ ] Task 1.2 后端：冻结前置校验增加「快照非空」
**描述**：`freeze` 在既有 `confirm`/范围评审/歧义/版本状态校验之外，增加 `rules` 非空校验；为空时抛既有业务异常类型，消息为人话（如「契约无有效条目，不可冻结」）。**不得放宽**任何既有前置校验。
**验收标准**：
- 空快照冻结被拒且返回人话原因，不静默成功
- 非空快照冻结行为与修复前完全一致（回归）
- 范围未 100% 评审时仍按 `_freeze_precondition` 原样拒绝
**涉及文件**：
- `test-platform-v2/backend/app/modules/aitde/contract/service.py:140-166` — `freeze` 增加非空守卫
**参考**：PRD §4 US-1 反例验收 / C216-1、C218-1 既有约束（不得另造容器、不得新造放行态）

#### [ ] Task 1.3 前端：契约页渲染规则与预期结果
**描述**：契约 Tab 消费已存在但闲置的 `ContractSnapshot/ContractRule/ContractOutcome` 类型，渲染规则列表（`rule_key`、标题、陈述、风险等级）与 `required_outcomes`；`snapshot` 为 `null` 或 `rules` 为空时显示明确空态并禁用「冻结契约」。
**验收标准**：
- 3 条已批准范围项 → 页面显示 3 条规则
- 空快照 → 空态文案 + 冻结按钮 disabled（含 title/tooltip 说明原因）
- 不新造类型，复用 `frontend/src/api/contract.ts:3-24` 既有定义
- Loading / Empty / Error 三态齐备（Design §3）
**涉及文件**：
- `test-platform-v2/frontend/src/pages/missions/contract.tsx:218-258` — 渲染快照内容
- `test-platform-v2/frontend/src/api/contract.ts:3-24` — 按需补 `snapshot` 到响应类型（不改既有类型定义）
**参考**：PRD §4 US-1 / Design 规范 §1

#### [ ] Task 1.4 API 契约同步
**描述**：`snapshot` 属新增响应字段，按 AGENTS.md §3.2 同步 OpenAPI schema，并确认无其他消费者依赖当前精简响应体。
**验收标准**：
- OpenAPI schema 含新字段
- 全仓 grep 确认 `/missions/{id}/contract` 的其他消费者不被破坏
**涉及文件**：
- 按仓库既有 OpenAPI 同步机制处理（Dev 阶段确认具体落点）
**参考**：AGENTS.md §3.2 / PRD §5 风险 1

#### [ ] Task 1.5 测试（TDD 先写）
**描述**：后端 Pytest 覆盖 snapshot 输出、空/损坏快照降级、空快照冻结被拒、非空冻结不回归；前端 Vitest 覆盖规则渲染与空态禁用冻结。
**验收标准**：先写失败测试 → 最小实现 → 全绿；记录退出码
**涉及文件**：按仓库既有测试目录约定
**参考**：SKILL.md 第 4 步 TDD 红绿重构

---

### S2 — 版本任务列表 + 侧边栏真实链接（DEF-20260905-002，P1）

#### [ ] Task 2.1 前端：`/version-tasks` 增加任务列表
**描述**：消费**已存在但零消费者**的 `listVersionTasks`，在 `/version-tasks` 展示本项目任务列表（标题、版本号、状态、创建时间），每行可点进 `/version-tasks/{id}`。建任务向导保留（同页分区或分 Tab，按 Design 规范）。列表须从接口取数，**不得依赖内存态**（当前 `useState` 刷新即丢是缺陷根因之一）。
**验收标准**：
- 有 ≥1 任务时列表可见且可点进详情
- 0 任务时显示空态（非空白），建任务入口仍可见
- 创建成功后刷新页面，新任务出现在列表
- **后端零改动**（`list_tasks` 已存在）；不得新建列表接口（C216-1）
- 列表受项目隔离约束
**涉及文件**：
- `test-platform-v2/frontend/src/pages/version-tasks/index.tsx:21-208` — 增加列表区与取数
- `test-platform-v2/frontend/src/api/versionTask.ts:81-89` — 直接复用 `listVersionTasks`
**参考**：PRD §4 US-2 / §5 依赖第 2 条

#### [ ] Task 2.2 前端：侧边栏分组子项恢复真实 href
**描述**：`SidebarMenuSubButton` 改为 `asChild` + react-router `Link to={child.path}`，使 5 个分组子项渲染为带 `href` 的锚点。保留既有 `onClick` 语义或确认 `Link` 已覆盖。`nav-config.ts` 的 `path` 数据本身正确（`seed.py:16-72` 播种），**不改数据层**。
**验收标准**：
- 「版本验收任务」「版本发布包」「智能测试任务」「报告中心」「缺陷管理」5 项均为 `<a href="/...">`，非 `href=null`
- `Tab` 可聚焦、回车可导航、右键可复制链接
- 5 项点击后均到达正确路由（逐项回归，高扇出改动）
- 无障碍树角色为 `link` 而非 `generic`
**涉及文件**：
- `test-platform-v2/frontend/src/layouts/MainNavRows.tsx:61-71` — 分组子项加 `asChild` + `Link`
- `test-platform-v2/frontend/src/components/ui/sidebar.tsx:649-676` — 只读确认 `Comp = asChild ? Slot : "a"` 机制，**不改此文件**
**参考**：PRD §1 表格第 2 行 / §5 风险 3

#### [ ] Task 2.3 交界标注（防重复修）
**描述**：Task 2.2 与 DEF-20260904-001（侧边栏死链，属下一批）同源。在本批 QA 报告与 Leader 判决中显式标注「href 缺失已在 Batch 230 修复」，下一批不得重复修。
**验收标准**：QA 报告含该标注；Leader 在 C 条件或判决中记录交界
**涉及文件**：QA 报告 / Leader 判决（非代码）
**参考**：PRD §3 非目标第 1 行 / §5 风险 5

#### [ ] Task 2.4 测试（TDD 先写）
**描述**：Vitest 覆盖列表渲染、空态、刷新后取数、行点击导航；侧边栏 5 项 href 与键盘可达性断言。
**验收标准**：先写失败测试 → 实现 → 全绿；含 a11y 断言（AGENTS.md §3.4）
**涉及文件**：按仓库既有测试目录约定
**参考**：SKILL.md 第 4 步

---

### S3 — 空跑不再伪装成已执行（DEF-20260905-003，P1）

#### [ ] Task 3.1 后端：`total=0` 不得置 `executed`，并回传原因
**描述**：`start_run` 中 `task.status = "executed"` 由无条件改为有条件——`not adopted_items` 时走阻塞路径（状态机已允许 `executing→blocked`），并让响应携带人话原因。**不得新造放行态**（C218-1）。原因承载方式（新增顶层 `reason` 字段 vs 复用 `failures`）由 Design 定，Dev 不得自行扩 schema。
**验收标准**：
- draft 无采纳条目 → 运行后任务状态非 `executed`，响应含原因文案
- 有 ≥1 采纳条目 → 正常执行并置 `executed`（既有通过路径零回归）
- `status="blocked"` 与 `blocked` 计数语义不再自相矛盾（要么计数反映阻塞，要么状态不由计数推导——按 Design 决议）
- 放行页与证据包生成不被连带打断（PRD §5 风险 2）
**涉及文件**：
- `test-platform-v2/backend/app/services/version_task_service.py:344` — `adopted_items` 过滤
- `test-platform-v2/backend/app/services/version_task_service.py:396-397` — `run_status="blocked"` 判定
- `test-platform-v2/backend/app/services/version_task_service.py:424` — 无条件 `task.status="executed"`
- `test-platform-v2/backend/app/schemas/version_task.py:199-214` — `VersionTaskRunOut`（按 Design 决议决定是否加字段）
**参考**：PRD §4 US-3 / §5 风险 2

#### [ ] Task 3.2 前端：运行态标签与 blocked 分支
**描述**：新增 RUN_STATUS 标签映射（与既有 `TASK_STATUS_LABEL` 并列），渲染运行态；`handleRun` 增加 `run.status === 'blocked'` 分支，用 warning/error toast 显示原因，不再恒发 `toast.success`。
**验收标准**：
- 接口 `blocked` → 界面显示「已阻塞」+ 原因，非「已执行」
- 不再出现「运行完成：0 通过 / 0 失败」的成功 toast
- 接口状态与界面标签语义一致（US-3 一致性验收）
- 成功路径 toast 不回归
**涉及文件**：
- `test-platform-v2/frontend/src/pages/version-tasks/[taskId].tsx:7-17` — 增加 RUN_STATUS 映射
- `test-platform-v2/frontend/src/pages/version-tasks/[taskId].tsx:58-69` — `handleRun` blocked 分支
- `test-platform-v2/frontend/src/pages/version-tasks/[taskId].tsx:128,133-144` — 渲染运行态与计数
**参考**：PRD §1 表格第 3 行 / §4 US-3

#### [ ] Task 3.3 测试（TDD 先写）
**描述**：Pytest 覆盖空方案阻塞、有方案正常执行、放行路径回归；Vitest 覆盖运行态标签与 blocked toast 分支。
**验收标准**：先写失败测试 → 实现 → 全绿；**必须含放行/证据包回归**（PRD §5 风险 2）
**涉及文件**：按仓库既有测试目录约定
**参考**：SKILL.md 第 4 步 / C218-1

---

### S4 — 自动发现失败不得报成功（DEF-20260905-004，P2）

#### [ ] Task 4.1 前端：补齐返回类型使漏检在编译期暴露
**描述**：`discoverAiModels` 返回类型声明 `ok`/`error`（可选 `kind`），对齐同文件 `testAiProviderConnection` 的既有写法。
**验收标准**：
- 类型含 `ok: boolean`、`error?: string`
- `npm run typecheck` 通过
- 不改后端信封（PRD §3 非目标：`ok:false` 装进 `R.ok` 属系统性模式，本批不动）
**涉及文件**：
- `test-platform-v2/frontend/src/api/aiConfig.ts:75-79` — 补类型
- `test-platform-v2/frontend/src/api/aiConfig.ts:57-69` — 只读参照 `testAiProviderConnection` 写法
**参考**：PRD §4 US-4 类型守卫验收

#### [ ] Task 4.2 前端：`handleDiscoverModels` 检查 `ok`
**描述**：await 后先判 `!res.ok` → `toast.error(res.error || '模型发现失败')` 并 return，不进入合并与成功 toast。
**验收标准**：
- Key 留空点自动发现 → 弹后端 `error` 原文，清单不变，无「已拉取厂商全量模型」字样
- 有效 Key 成功 → 成功 toast + 清单更新为接口返回值（不回归）
- 与 `testAiProviderConnection`（`ai-config/index.tsx:198-200`）保持同一处理模式
**涉及文件**：
- `test-platform-v2/frontend/src/pages/ai-config/index.tsx:242-270` — `handleDiscoverModels`，重点 `:254` 合并与 `:263` 成功 toast
**参考**：PRD §1 表格第 4 行

#### [ ] Task 4.3 测试（TDD 先写）
**描述**：Vitest 覆盖 `ok:false` 弹错误且清单不变、`ok:true` 弹成功且清单更新。
**验收标准**：先写失败测试 → 实现 → 全绿
**涉及文件**：按仓库既有测试目录约定
**参考**：SKILL.md 第 4 步

---

### S5 — 缺陷可按编号检索（DEF-20260905-005，P2）

#### [ ] Task 5.1 后端：搜索谓词增加 `defect_id`
**描述**：`keyword` 过滤由仅 `title.contains` 改为 `or_(title.contains, defect_id.contains)`。**必须确保 `project_id` 等项目隔离约束在 OR 之外**（括号优先级），不得因新增 OR 而跨项目泄漏。是否一并匹配 `external_id`（禅道/Jira）由 Design 定。
**验收标准**：
- 搜「DEF-20260904」命中全部同日期缺陷；搜「DEF-20260904-010」命中 1 条
- 搜标题关键词命中集合与修复前一致（不回归）
- 跨项目隔离仍生效（构造两项目同编号数据验证）
- 前端参数名不变（仍 `keyword`），无需改调用方
**涉及文件**：
- `test-platform-v2/backend/app/services/defect_service.py:87-88` — 搜索谓词
- `test-platform-v2/backend/app/models/defect.py:18` — 只读确认 `defect_id` 列（`String(50)`）
**参考**：PRD §1 表格第 5 行 / §5 风险 4

#### [ ] Task 5.2 前端：placeholder 与实际能力一致
**描述**：搜索框 placeholder 由「搜索缺陷标题」改为反映可搜范围（如「搜索标题或编号」）。
**验收标准**：文案与实际能力一致；不改参数名与防抖逻辑
**涉及文件**：
- `test-platform-v2/frontend/src/pages/defect/DefectFilterBar.tsx:69-72` — placeholder
**参考**：PRD §4 US-5

#### [ ] Task 5.3 测试（TDD 先写）
**描述**：Pytest 覆盖按编号搜、按标题搜不回归、跨项目隔离。
**验收标准**：先写失败测试 → 实现 → 全绿；**必须含隔离用例**
**涉及文件**：按仓库既有测试目录约定
**参考**：PRD §5 风险 4

---

### S6 — 范围评审记录操作人（DEF-20260905-006，P2）

#### [ ] Task 6.1 后端：API 层向下传 username
**描述**：`mission_scope.py` 的分析与评审端点把 `current.user.username` 传入服务层（当前只传 `current.user.id`）。如需 `ip`，按 `defect.py:21-33` 既有模式接收 `Request`。
**验收标准**：服务层签名收到 username；不改 `write_audit` 写入器本身
**涉及文件**：
- `test-platform-v2/backend/app/api/v2/mission_scope.py:31-32,64-65` — 传参
- `test-platform-v2/backend/app/api/v1/defect.py:21-33` — 只读参照既有正确写法
**参考**：PRD §1 表格第 6 行

#### [ ] Task 6.2 后端：`_audit` 去掉硬编码空 username
**描述**：`scope/service.py` 的 `_audit` 由硬编码 `username=""` 改为接收并透传真实 username；`analyze_scope` 与 `review_scope` 两条调用链都覆盖。
**验收标准**：
- `scope:review` 与 `scope:analyze` 审计行操作人 = 登录名，与 `defect:create` 同口径
- 两条链路都非空（不得只修评审漏掉分析）
**涉及文件**：
- `test-platform-v2/backend/app/modules/aitde/scope/service.py:136-157` — `_audit`，重点 `:150`
- `test-platform-v2/backend/app/modules/aitde/scope/service.py:70` — `analyze_scope` 调用点
- `test-platform-v2/backend/app/modules/aitde/scope/service.py:111-113` — `review_scope` 调用点
**参考**：PRD §4 US-6

#### [ ] Task 6.3 同类排查
**描述**：grep AITDE 其余服务层是否存在同样的 `username=""` 硬编码；有则一并修正，无则在 QA 报告写明排查范围与结论。
**验收标准**：QA 报告含排查结论（命中清单或「仅此一处」）
**涉及文件**：`test-platform-v2/backend/app/modules/aitde/**`
**参考**：PRD §4 US-6 同类排查验收

#### [ ] Task 6.4 测试（TDD 先写）
**描述**：Pytest 覆盖分析与评审两类事件的操作人写入。
**验收标准**：先写失败测试 → 实现 → 全绿
**涉及文件**：按仓库既有测试目录约定
**参考**：SKILL.md 第 4 步

---

### S7 — 术语拼写与 404 横幅（DEF-20260905-007 P3、DEF-20260905-009 P3）

#### [ ] Task 7.1 前端：修正 Ambiguitity
**描述**：`contract.tsx:175` 的「歧义（Ambiguitity）」改为「歧义（Ambiguity）」。
**验收标准**：页面渲染正确拼写；全仓 grep 无其他 `Ambiguitity` 残留
**涉及文件**：
- `test-platform-v2/frontend/src/pages/missions/contract.tsx:175`
**参考**：PRD §1 表格第 7 行

#### [ ] Task 7.2 前端：横幅不再出现在 404 上
**描述**：按 Design 决议二选一——(a) `LegacyNoticeBanner` 前缀匹配改为路径段边界（`pathname === p || pathname.startsWith(p + '/')`）；或 (b) 更健壮：命中 404 splat 路由时抑制横幅（`useMatches()` 判叶节点是否 `*`）。PRD §4 US-7 要求「不得依赖易碰撞的裸前缀匹配」，Design 须在两者中给出决议与理由。
**验收标准**：
- `/defects`、`/environments` 只渲染 404 空态，无收敛横幅
- `/defect`、`/environment` 及其子路径（如 `/defect/123`）横幅照常渲染（不回归）
- 任一未注册路由均不渲染横幅（不只修这两个已知案例）
- **不实现**「相近模块建议」（PRD §3 非目标）
**涉及文件**：
- `test-platform-v2/frontend/src/components/legacy/LegacyNoticeBanner.tsx:8-26` — 匹配逻辑，重点 `:26`
- `test-platform-v2/frontend/src/layouts/MainLayout.tsx:460` — 只读确认渲染位置（横幅在 `<Outlet/>` 之上，404 是其子路由）
- `test-platform-v2/frontend/src/router/index.tsx:503` — 只读确认 `{path:'*',element:<NotFound/>}`
**参考**：PRD §1 表格第 8 行 / §4 US-7 健壮性验收

#### [ ] Task 7.3 测试（TDD 先写）
**描述**：Vitest 覆盖横幅在真实历史入口显示、在未注册路由不显示、在历史入口子路径显示；拼写快照断言。
**验收标准**：先写失败测试 → 实现 → 全绿；**必须含子路径不回归用例**
**涉及文件**：按仓库既有测试目录约定
**参考**：PRD §4 US-7

---

## 质量要求（全批统一）

- [ ] 响应式（Desktop + Tablet）——S1 契约规则列表、S2 任务列表为表格/列表类，须核对断点
- [ ] OpenAPI 同步——S1 Task 1.4 为强制项（新增响应字段）
- [ ] 单元测试覆盖——每个 Slice 均含 TDD 任务（1.5 / 2.4 / 3.3 / 4.3 / 5.3 / 6.4 / 7.3）
- [ ] 无障碍（ARIA/键盘）——S2 Task 2.2 为核心项（href/焦点/角色）；S1 冻结禁用态须可被读屏感知
- [ ] 无 `console.log` / `print` / `breakpoint` / `debugger` 遗留（AGENTS.md §3.1）
- [ ] 无硬编码密钥（AGENTS.md §3.1）
- [ ] 前端 useEffect 清理、useCallback 无循环依赖、无 N+1 请求、TabsContent forceMount、每个 GET 只 1 次有效请求（AGENTS.md §3.4）——S2 列表取数与 S1 快照取数须逐条核对
- [ ] 提交前 `pwsh scripts/git/scan-common-bugs.ps1`，HARD=0；`pwsh scripts/git/dev-gate.ps1` 通过（AGENTS.md §3.1）
- [ ] 全量回归已记录：后端 `pytest`、前端 `npm test`；有基线失败须列出基线与本分支失败集合并确认无新增（AGENTS.md §3.1）
- [ ] 文档保鲜：CLAUDE.md / README.md / ADR 若有模块或约定变化须同步（AGENTS.md §3.3）
- [ ] 只提交本批范围文件，无备份文件、无 `.db`、无 IDE 临时文件（AGENTS.md §3.5）

## 交付顺序与提交纪律

1. 每 Slice 结束**立即 commit**（工作树可能被外部进程重置，见 `worktree-reset-hazard`），提交前 `git status --short` → `git add -- {明确文件}` → `git diff --cached --name-status` 核对，防夹带。
2. 总确认前**只本地提交，不推送**。首轮 QA 证据完成后做一次总确认（推送 + Draft PR + required checks 通过后合入），确认后不再逐次询问（AGENTS.md §2.4 Agent Team 例外）。
3. 提交信息格式：`fix(batch-230): {切片描述}`（S2 因含新视图可用 `feat(batch-230):`）。
