---
title: "ADR-0021: AITDE V3.1 统一执行 + Proof Replay（确定性结论、无 AI 裁决）"
owner: "qa-team"
last_reviewed: "2026-08-29"
status: "已采纳"
tags: ["adr", "aitde", "v3.1", "execution"]
related: ["docs/aitde/versions/V3.1_Detailed_Development_Implementation_Plan.md"]
---

# ADR-0021: AITDE V3.1 统一执行 + Proof Replay

## 状态

已采纳

## 日期

2026-08-29

## 背景

V3.0 把承载对象迁移到 `TestScenario + Oracle` 后，执行事实仍然散落在三条旧的互不连通的链路上（API 任务、UI 运行、TestExecution）。历史上普遍存在**假成功 / 假失败**：`HTTP 200 → PASS`、看到 Toast → PASS、脚本异常被当成 `BUSINESS_FAIL`，且没有统一证据与可回放记录。

若不决策，V3.1 之后无法可靠地区分「业务失败」「执行失败」「数据/环境失败」，也无法对单个 Run 给出可留档的 proof replay。

## 决策

把现有 API/UI/TestExecution 的执行事实统一到一条链：`Scenario → ExecutionRun → ExecutionStep → AssertionResult → EvidenceArtifact → ReplayManifest`，并从架构上第一次控制假成功/假失败。

- **Run 永远绑定** `scenario_version_id + contract_version_id + environment_snapshot_id`。
- **`runtime_status`（调度）与 `outcome`（结论）分离**。
- **AI 不参与正式 Outcome 计算**；`OutcomeClassifier` 是确定性决策表。
- **PASS 必须满足 Required Oracle 全部已评估且 Required Evidence 完整**；否则降级为 `INCONCLUSIVE`。
- **Runtime/Data/Environment 问题不能伪装成 BUSINESS_FAIL**（决策表严格顺序：ENV_FAIL → DATA_FAIL → AUTOMATION_FAIL → ASSERTION_ERROR → BUSINESS_FAIL → INCONCLUSIVE → PASS）。
- **Evidence 先清洗再落对象存储**；未 `SANITIZED` 不可成为正式 Replay。
- **Production 默认只读**；Legacy API/UI Runner 先通过 Bridge 接入，不在本版删除。
- **Shadow Audit** 记录 CONFIRMED/FALSE_PASS/FALSE_FAIL，**不改历史 outcome**（仅作监控/学习信号）。

分阶段实施：V3.1 只做执行/断言/证据/回放；DB 造数（V3.2）、Browser Command IR（V3.3）、Temporal（V3.4）、Build 监听（V3.5）、Production Evidence（V3.6）、Smart Regression（V3.7）、AI Auto Healing（V3.8）留给后续版本。

## 后果

### 正面影响

- ✅ 假成功/假失败在架构上被阻断（决策表 + EvidenceCompleteness + 无 LLM 断言）。
- ✅ 每个 Run 有环境快照指纹、可审计证据、append-only Replay。
- ✅ Legacy 链路可平滑桥接接入，无需破坏旧记录。

### 负面影响 / 权衡

- ⚠️ 执行模型从旧单表变为多表（Adapter/Snapshot/Run/Step/Assertion/Evidence/Manifest），写路径更复杂。
- ⚠️ 对象存储成为证据强依赖；存储故障时必须停止 `Evidence COMPLETE` 判定（已作为不变量用单元测试固化）。
- ⚠️ `/api/v2` 新增 15 个路由与 4 个 Migration（M31-1..4），上游依赖场景/契约模型。

## 弃选方案

### 方案 A: 在旧执行表上打补丁（最小改动）

- 优点：改动面小、落地快。
- 缺点：无法统一 `outcome` 语义与证据模型，假成功问题无法根治；旧表没有版本绑定与快照。
- 放弃原因：不符合 V3.1「第一次从架构上控制假成功/假失败」的版本目标。

### 方案 B: 复用 `TestCase` 作为执行载体

- 优点：与旧资产对齐。
- 缺点：V3.0 已把 canonical 事实源迁移到 `Scenario`，回到 TestCase 会破坏 V3.0 不变量。
- 放弃原因：与 V3.0 结论冲突（`docs/aitde/v3.0/qa-policy-mapping.md`）。

## 关联

- 相关文档: `docs/aitde/versions/V3.1_Detailed_Development_Implementation_Plan.md`、`docs/aitde/v3.0/qa-policy-mapping.md`
- 相关模块: `test-platform-v2/backend/app/modules/aitde/{execution,environment,assertion,evidence}`
