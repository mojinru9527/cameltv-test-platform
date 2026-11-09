# Batch 274 — AIQE Spec Review：PRD Summary

> **部门**：🟦 Product
> **日期**：2026-11-09
> **Executor**：Claude Code
> **分支**：feature/aitde-v39-reality-gate（评审任务，不另开 worktree）
> **批次模式**：完整批次（六部门工件齐全，Dev 产出为"落地就绪度审计"而非代码）

---

## 1. 问题陈述

用户在 docs/platform-refactor/ 下得到了两份互为补充的 AI 测试平台落地文档：

- **12 号**（`12-ai-quality-agent-landing-plan.md`，957 行）：本 Session 第一轮产出，侧重**现有代码接缝 + AITDE 教训 + Agent Skills 可移植**。
- **13 号**（`13-ai-quality-agent-merged-spec.md`，2899 行）：把 12 号与"另一 Agent 的 v2.0 Spec"合并，吸收对方的**数据模型 / 状态机 / 噪音治理 / E2E 验收 / OSS 准入 / Agent 评估基准 / 安全治理**七大强项。

13 号 frontmatter 现在是 `status: proposal`。用户选择"走 Agent Team 门禁评审"把这份规格从 proposal 推到 active 或打回。

**本批次要回答的问题**：13 号是否可以作为 CamelTv AIQE 的"权威工程规格 v1"合入？

## 2. 成功指标（本次评审）

| 维度 | 指标 | 阈值 |
|------|------|------|
| 完整性 | 7 个重点决策点全部有明确结论（§0/§4/§5/§6/§11/§14/§19） | 100% |
| 一致性 | 规格内部无自相矛盾条款 | 0 处矛盾 |
| 与现有代码对账 | §18.5 列的 8 个接入点经抽样核对与当前仓库一致 | ≥ 7/8 |
| 与现有 ADR 对账 | 不与 ADR-0014/0015/0019/0020 冲突 | 0 处冲突 |
| 与 11 号方案 / 10-07 评估对账 | 继承"不恢复 AITDE / 不恢复 DSH / 报告中心" 等已删决策 | 0 处回潮 |
| 与 C-CONDITIONS.md 对账 | 相关 Open 条件（C205-1 等）在规格里有归属 | ≥ 50% 可对上 |

## 3. 非目标（本次评审不做）

**延续 C-CONDITIONS.md 中以下 Open 条件不纳入本次评审范围**（后续批次处理）：

- C205-1 ~ C205-3：足球/篮球接口用例参数精修 → 由 SPORT 系列批次处理，不是 AIQE 规格范围。
- C204-1/2/3、C203-1：参数真实/假数据成功 → 同上。
- C84-1 iOS 真机：规格 §13 已登记，解决方案三选一留给用户拍板，本批不定。
- 外部阻塞项（Deferred 条目，约 15 项）：维持 Deferred。

**明确不做**：
- 不实际改代码（本批无 TA 执行，Dev 产出是"落地就绪度审计"）；
- 不改 13 号规格书本身（修改意见写在 QA + Leader verdict）；
- 不评审 11 号方案已决定的删除清单（AITDE/DSH/报告中心等保持删除）。

## 4. 用户故事

### US-274-1：规格合入决策

**作为**：用户（CamelTv 平台负责人）
**我想**：知道 13 号规格书是否可以作为未来 20 周 TA-000 … TA-045 开发的权威事实源
**以便**：对 P0 清零 / 代码审计 / OSS PoC 等后续批次给出明确起点

**Given / When / Then**（验收标准）：
- **Given** 13 号规格书 2899 行 / 22 张表 / 10 ADR / 45 个 TA 任务 / 10 条 E2E 验收
- **When** 六部门评审全部完成
- **Then** 必须有 Leader verdict 给出 `合入 / 修改后合入 / 拒绝` 三选一的明确结论
- **And** 若"修改后合入"必须列出需改条目（M-1 ... M-N）每条指到 §章节 + 建议

### US-274-2：七个重点决策点逐一答复

**作为**：用户
**我想**：对 7 个决策点（P0 清零顺序 / 数据模型重复风险 / 状态机完备性 / WorkflowDefinition 护栏 / 噪音治理通用性 / OSS 版本锁 / 工期估算）各得到一个明确观点
**以便**：评审完成后不留模糊

**Given / When / Then**：
- **Given** 用户已列出 7 个决策点
- **When** QA 报告完成
- **Then** 每个决策点必须有 PASS / NEEDS_FIX / UNKNOWN 三选一结论
- **And** NEEDS_FIX 必须链入 Leader verdict 的 M-N 条目

### US-274-3：评审不污染当前分支

**作为**：用户
**我想**：评审工件产出但不干扰 AITDE v3.9 Reality Gate 的进行中工作
**以便**：当前 `feature/aitde-v39-reality-gate` 分支继续沿用

**Given / When / Then**：
- **Given** 当前分支是 feature/aitde-v39-reality-gate
- **When** 本批次工件写入 work-logs/
- **Then** 不 commit / 不 push / 不碰 test-platform-v2/ 下任何文件
- **And** 工件以 untracked 状态保留在 working tree，供用户决策后另做处置

## 5. KB 检索引用（Product 开工前置）

本批次是 **规格评审** 不是代码交付，KB 检索按"评审参考"口径：

| 检索项 | 发现 | 本批处理 |
|-------|------|---------|
| AITDE 失败模式 | 评估报告已归档：180 文件 22.9k 行 0 真实 Run；根因三条（执行链不落地 / 上手成本 / 多 AI 并存） | 评审时用作"13 号是否重蹈 AITDE 老路"的尺子 → §6/§24 ADR-AIQE-008 |
| 批次 212/215 旧测试计划删除 | 已合入 | 评审时确认 13 号不恢复 TestPlan |
| Batch 190 DSH AgentTeams 迁移 | 已合入 | 评审时确认 13 号 §10 Agent 服务不依赖 DSH Agent 队列 |
| Batch 258-261 B1-B4（ExecutionJob + cameltv-node + 执行沙箱 + 影响图 + 体育试点） | 已合入 | 评审时确认 13 号 §7 Driver 建立在这套基础之上 |
| Batch 271/272 菜单权限对账 + 导航瘦身 | 已合入 | 评审时确认 13 号不在 UI 顶层增一级入口 |
| Batch 273 P0-P3 安全与韧性整改 | 已合入 | 13 号 §0 的 5 条 P0 需与 batch-273 的 C273-x 做对账（见 QA 报告） |

## 6. C-CONDITIONS 检查结果

| C 条件 | 状态 | 本批处置 |
|--------|------|---------|
| C205-1 ~ 3 | Open | 非本批范围 |
| C204-1/2/3 | Open | 非本批范围 |
| C203-1 | Open | 非本批范围 |
| C84-1 iOS 真机 | Open | 13 号 §13 已登记为三选一待定，本批不定 |
| C263-1 /uitest 内置浏览器收口 | Open | 13 号 §0 P0-4 已承接，本批确认承接方向正确 |
| C273-1 ~ C273-5 | Open（需对账） | 13 号 §0 的 P0 必须与 C273-1/5 对齐，详见 QA 报告 |

## 7. 边界与约束

- **不改 13 号文件**：修改意见只写在 QA 报告 + Leader verdict；若 Leader verdict = "修改后合入"，由后续 batch-275 开 docs-only 轻量批次改 13 号。
- **不开新 worktree**：本批无代码改动，worktree 隔离不适用。
- **不创建 CI 门禁**：本批不涉及 test-platform-v2/ 代码，QA 硬门禁改为"规格一致性检查 + 与现有 ADR 对账"，不跑 build/typecheck。
- **不提交**：本批工件以 untracked 保留；用户拍板后再决定是否正式 commit / PR。

## 8. 输出清单

| 工件 | 作用 |
|------|------|
| batch-274-aiqe-spec-review-prd-summary.md（本文件） | 评审范围 + 成功指标 + 用户故事 |
| batch-274-aiqe-spec-review-pm-plan.md | 把评审拆成 7 个评审任务（对应 7 个决策点） |
| batch-274-aiqe-spec-review-design-spec.md | 规格内部一致性 + 与现有 ADR/代码对账的检查清单 |
| batch-274-aiqe-spec-review-dev-plan.md | 落地就绪度审计（而非编码计划） |
| batch-274-aiqe-spec-review-qa-report.md | 7 决策点逐一 PASS/NEEDS_FIX + 复盘卡 |
| batch-274-aiqe-spec-review-leader-verdict.md | 最终判决 + 流程回写 + 复盘卡 |
| kanbans/DEV-batch-274-aiqe-spec-review.md | 看板 |
