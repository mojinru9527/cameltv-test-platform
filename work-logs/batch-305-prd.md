# Batch 305（M4 / TA-027）— 一键回归：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-305-m4-one-click-regression · **基线**：origin/main `6ea29ccc5`
> **里程碑**：M4 第 3 批

## 1. 问题

缺陷修复后需要“一键回归”：记录修复 SHA、关联旧/新 Run、展示断言对比。手工回归容易丢旧 Run
或无法判断“已修复 / 回归失败 / 仍失败”。

## 2. 目标

1. `defect_regressions` 表（defect/fixed_sha/previous_run_id/verification_run_id/status）；
2. `POST /defects/:id/regressions`（一键回归入口）；
3. `compare_runs(previous, current)`：fixed / regressed / still_failing / new_assertions，
   纯函数、不改旧 Run；
4. 前端 `<RegressionDialog />`（SHA 校验）+ `<RunComparison />`（对比视图）；
5. 迁移 `20261120`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 回归记录旧/新 Run | `test_create_regression_records_runs` |
| A2 | 无验证 Run 为 pending | `test_pending_regression_without_verification_run` |
| A3 | 缺陷不存在/短 SHA 拒绝 | `test_unknown_defect_rejected` / `test_short_sha_rejected` |
| A4 | 对比四分类 | `test_compare_runs_fixed_regressed_failing` |
| A5 | 旧 Run 不被修改 | `test_compare_does_not_mutate_previous` |
| A6 | 多次回归留存 | `test_regression_rows_persisted_per_attempt` |
| A7 | 对比视图/对话框 | `RegressionComponents.test.tsx`（4） |
| A8 | 路由基线 | 322 → 323 |
| A9 | 全量 + ratchet | backend 1584；frontend 556；typecheck/build |

## 4. 非目标

- 真实触发新 Run（服务记录 verification_run_id，由调度器接）；
- 历史回归趋势图。
