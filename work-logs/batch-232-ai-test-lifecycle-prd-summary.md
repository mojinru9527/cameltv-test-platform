# Batch 232 - AI Test Lifecycle PRD Summary
> **Product** | Date: 2026-09-07 | Status: Approved

## 1. 问题陈述

测试人员输入需求后，当前平台把 VersionTask、AITDE Mission、API/UI 执行记录分别保存，缺少正式关联。Mission 概览又只展示六张固定说明卡，导致用户无法回答四个基本问题：本次需求拆出了什么、生成了哪些用例、哪些用例实际执行并留下证据、失败后是否已建缺陷并复验。

生产任务“体育平台 16.0.0 篮球多项目适配”的核查证据表明：Mission #34 只有一个通用范围项和一个通用场景，四条执行记录均未形成有效执行结果；VersionTask #6 虽在 scope JSON 中写了 mission_id，但 `source_mission_id` 为空，API/UI 运行也没有进入 Mission 主链。这不是文案问题，而是事实链断裂。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| VersionTask 与阶段 Mission 可追踪率 | 仅 JSON 弱引用 | 100% 使用数据库外键 | 本批 QA |
| 用例分类完整率 | 无显式分类 | 每条场景均有功能/API/UI 类型 | 生成与读取时 |
| 需求角色完整率 | 无显式分类 | 每条场景均有新增/变更/受影响基线角色 | 生成与读取时 |
| 逐用例执行可追踪率 | 页面无法汇总 | 每条用例展示运行次数、最新结果、证据数、缺陷数、复验关系 | 本批 QA |
| Mission 主链真实性 | 六张静态说明卡 | 六阶段均展示持久化数量与状态 | 本批 QA |

## 3. 非目标（本次不做）

- 不再创建新的“AI 全链路任务”容器；VersionTask 继续作为版本级事实根，Mission 承载阶段工作。
- 不重写现有 API、UI、手工执行引擎；复用 AITDE ScenarioAdapter、ExecutionRun、EvidenceArtifact 与 `parent_run_id`。
- 不在本批自动替用户创建或执行 16.0.0 生产回归；能力合入并发布后，才在生产平台创建正式任务并使用指定 Test5/生产环境执行。
- C230-1 涉及生产操作审计操作者透传，本批不修改相关权限与审计链，明确豁免。
- C225-1 是 B1-B15 的全平台终验，不在本批关闭；本批只为其中的任务追踪链补能力。
- C227-1 纳入：required checks 全绿并完成最终审计前，Leader 不得批准合入。

## 4. 用户故事与验收标准

### US1 从需求形成三阶段测试工作

As a 测试工程师, I want 一个版本任务能关联需求测试、测试环境版本回归、生产回归三个 Mission, so that 我能区分每条执行属于哪个阶段。

验收：Given 同一 VersionTask / When 创建或关联 Mission / Then Mission 通过正式 `version_task_id` 归属版本任务，且 FEATURE、VERSION、REGRESSION 分别显示“需求测试”“版本回归”“生产回归”。

### US2 AI 输出可执行、可追溯的三类用例

As a 测试工程师, I want AI 场景明确标注功能、接口、UI 以及需求角色和模块, so that 我能看清新增需求和历史影响面。

验收：Given 冻结契约 / When AI 生成场景 / Then 每条场景必须包含 `case_type`、`requirement_role`、`module_key` 和非空 `source_refs`；AI 响应缺字段时失败关闭，不写入含糊场景。

### US3 每条用例独立留痕

As a 测试工程师, I want 每条用例的每次执行都有结果、证据和复验链, so that 验收结论可回放。

验收：Given 某 Mission 有场景和执行 / When 打开概览 / Then 每条场景展示执行次数、最新结果、证据数量、关联缺陷数量；重试运行通过 `parent_run_id` 指向原运行。

### US4 失败转缺陷并复验

As a 测试工程师, I want 从失败运行创建缺陷并在修复后重试, so that 缺陷和复验不会脱离原用例。

验收：Given 失败 ExecutionRun / When 创建缺陷 / Then 缺陷保存 `aitde_run_id`；When 对原运行执行 retry / Then 新运行作为子运行出现，概览显示待复验或复验结果。

### US5 概览呈现真实主链

As a 测试工程师, I want 概览直接说明每一阶段处理了什么、还缺什么, so that 我无需逐 Tab 猜测执行状态。

验收：Given Mission 有部分或完整数据 / When 打开概览 / Then 资料、分析、契约、用例、执行、验收六阶段显示真实数量、状态和缺口；加载失败与真空数据明确区分。

## 5. 技术考量

- 数据库迁移必须接在 `20260913_b231_traceability_truth` 单头之后，并兼容 SQLite/PostgreSQL。
- 所有聚合查询必须限制 `project_id`，不得跨项目读取 VersionTask、ExecutionRun 或 Defect。
- 场景生成保持 Oracle 信任守卫：AI 推断 Oracle 不得静默成为 required。
- 逐用例明细应由一次聚合 API 返回，前端不得循环发 N+1 请求。
- 旧 Mission/场景缺新字段时使用明确的 `UNCLASSIFIED` 历史态，不伪装成已完成分类。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本地验证 | 开发/QA | 相关 Pytest、Vitest、类型检查、构建、迁移单头通过 |
| Draft PR | 仓库维护者 | required checks 全绿、最终审计通过 |
| 生产发布 | 测试团队 | 发布流水线成功、Mission 概览真实数据显示正常 |
| 16.0.0 重建任务 | 业务测试 | 三阶段和三类用例完整、逐条执行有证据 |

## 7. 技能使用

- `cameltv-agent-team`：采用完整六部门批次并保留工件、看板和 PR 门禁。
- `cameltv-bug-guard`：约束迁移单头、租户隔离、React 请求去重与错误态。
- `cameltv-ui-conventions`：概览使用语义状态色、四态和响应式布局。
- `writing-plans`：按 TDD 小步骤拆分实现与验证。
- `karpathy-guidelines`：复用现有事实模型，限制改动范围，拒绝新增平行容器。
