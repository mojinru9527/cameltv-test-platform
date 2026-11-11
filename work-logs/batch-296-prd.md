# Batch 296（M3 / TA-021）— A3 Workflow Planner：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-296-m3-workflow-planner · **基线**：origin/main `94d1ade38`
> **里程碑**：M3 第 6 批

## 1. 问题

需求/用例之后需要生成可执行 Workflow，但 AI 容易产出环、悬空依赖、未注册 driver，
甚至自行“批准”直接执行。TA-021 要求：依赖关系可对照标注样本验证，未批准不得执行。

## 2. 目标

1. `WorkflowPlannerAgent`：输出 Workflow Graph + rationale；
2. 必须通过 `workflow_validator`（环/依赖/变量/driver/重试/断言）；
3. `approval_status` 固定 `pending`，自批直接拒绝；
4. `dependencies_match()` 对照 20 个已标注业务工作流；
5. `ensure_executable()`：非 approved 抛 `WorkflowNotApproved`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 合法规划 pending | `test_valid_plan_is_pending` |
| A2 | 自批拒绝 | `test_self_approval_rejected` |
| A3 | 环拒绝 | `test_cycle_rejected` |
| A4 | 未注册 driver 拒绝 | `test_unknown_driver_rejected` |
| A5 | 依赖比对 | `test_dependencies_match` |
| A6 | 未批准不可执行 | `test_unapproved_cannot_execute` |
| A7 | 20 个标注工作流 | `test_twenty_labeled_workflows` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 LLM（fake 注入）；
- Workflow 入库/审批 UI（已有 workflow_definitions，后续接）；
- 条件边规划（调度器当前只支持成功边）。
