---
title: "版本发布节奏：合代码 ≠ 发版本"
owner: "qa-team"
last_reviewed: "2026-08-07"
status: "active"
expires: "2026-12-31"
tags: ["release", "cadence", "release-train", "deployment", "batch"]
related: ["../../AGENTS.md", "0014-single-main-trunk-ai-worktrees.md", "0015-operations-release-control-plane.md", "local-dev-workflow.md", "pipeline-modes.md"]
---

# 版本发布节奏：合代码 ≠ 发版本

> 事实源：本文档定义 CamelTv test-platform 的版本发布节奏。
> 目标：把「合入主干」与「版本发布」解耦——主干随时合并，发布按固定窗口聚合。

## 1. 核心原则

1. **合入 main 不等于发布**。功能分支 PR 通过 required checks 后即可合入主干，主干始终保持最新稳定状态（ADR-0014 单一主干）。
2. **版本发布 = 聚合窗口**。多个批次按节奏聚合为一个版本（`release/vX.Y.Z`），一次 test 部署 + 一次生产验收，而不是每个批次都单独发布。
3. **批次粒度可合并**。同域小修复合并为一个轻量批次；纯文档/证据改动合并提交，不单独开 PR。

## 2. 发布火车（Release Train）

| 项 | 默认节奏 | 说明 |
|----|---------|------|
| 主干合并 | 随时 | PR 门禁通过即合入，不等发布窗口 |
| 版本聚合 | 每 2–3 天或每周 | 从最新 main 切 `release/vX.Y.Z`，或直接在 main 打 tag + release notes |
| test 部署 | 每日固定窗口 | 定时构建最近 main（见 §3） |
| 生产发布 | 每周 release 窗口 + 审批 | 只接受 `TEST_VERIFIED` 的同一制品（ADR-0015） |

### 2.1 release 分支流程（需要稳定窗口时）

```
main（已合入多个批次）
  → git fetch origin && 从最新 origin/main 切 release/vX.Y.Z
  → 稳定性修复：hotfix/ 分支 PR 合回 release 分支与 main
  → release 验收通过 → 打 tag vX.Y.Z + release notes
  → release/vX.Y.Z 合回 main（如含修复）
```

若单次聚合内容少、无需稳定窗口，可省略 release 分支，直接对 main 打 tag。

### 2.2 版本号

- 采用 `vX.Y.Z`：X 大版本（架构/重大变化），Y 功能版本（一个发布窗口），Z 补丁（hotfix/小修）。
- 每打一个 tag，写 release notes（包含批次清单 + 已知风险 + 回滚目标）。

## 3. 部署节奏

| 环境 | 触发 | 说明 |
|------|------|------|
| test | 每日固定窗口自动部署最近 main | Jenkins 每日构建 + Deploy Test 阶段；合入 main 本身不触发部署 |
| staging | 手动 / release 窗口 | 预发布验证 |
| prod | 每周 release 窗口 + 审批 | ADR-0015 晋级：`TEST_VERIFIED` → 审批 → 备份 → 迁移 → 发布 → 冒烟 |

## 4. 批次粒度合并指引

- **同域小修复合并**：多个同域小修复（如本周 UI 修复）归并为一个轻量批次，走一次六部门流水线，而不是每个修复一个批次。
- **纯文档/证据合并**：README/ADP/work-logs 类改动合并提交，不单独开 PR。
- **轻量批次判定不变**：是否引入新行为/新接口/新配置/新依赖仍是完整 vs 轻量的唯一标准（见 pipeline-modes.md）。

## 5. 与现有流程的关系

- AGENTS.md §2.1.1 批次生命周期：批次完成后先合入主干，再从最新主干开新批——不变；本文档补充「合入主干 ≠ 发布」。
- ADR-0015：生产只接受 test 验证通过的同一 release manifest；发布窗口与审批在控制面执行。
- 每日定时回归（api-regression、pr-check 观察、responsive-e2e、prod-smoke）兜底主干健康，替代原「push 到 main 双端全量重跑」。

## 6. 变更记录

| 日期 | 批次 | 变更摘要 |
|------|------|---------|
| 2026-08-07 | Batch 115 | 新增发布节奏事实源：合代码 ≠ 发版本；发布火车 + 定时部署窗口 + 批次合并指引 |
