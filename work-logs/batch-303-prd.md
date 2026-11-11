# Batch 303（M4 / TA-025）— Counterfactual Replay Coordinator：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-303-m4-counterfactual-replay · **基线**：origin/main `1913350f6`
> **里程碑**：**M4 第 1 批**

## 1. 问题

失败归因需要“单变量反事实实验”来验证假设；若一次改多个变量，结论不可信；重复调用还会
重复创建验证 Run。TA-025 要求：E1-E6 每个单变量实验落 `verification_run_id`，双变量被拒，
幂等检查通过。

## 2. 目标

1. `triage_experiments` 表 + 迁移 `20261118`；
2. E1-E6 预置实验（replay / disable flag / isolated profile / reset data / isolate concurrency /
   normalize network）；
3. `run_experiment()`：`change` 必须且只能 1 个变量，否则拒绝；
4. 每次实验记录 `verification_run_id`（可显式传入，否则生成）；
5. `idempotency_key` 唯一：重复调用返回原记录，不重复创建。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | E1-E6 各落 verification_run_id | `test_each_experiment_records_verification_run` |
| A2 | 双变量拒绝 | `test_double_variable_rejected` |
| A3 | 空变更拒绝 | `test_empty_change_rejected` |
| A4 | 未知实验拒绝 | `test_unknown_experiment_rejected` |
| A5 | 幂等返回同记录 | `test_idempotency_returns_same_record` |
| A6 | 显式 verification_run 保留 | `test_explicit_verification_run_preserved` |
| A7 | 不同 key 两行 | `test_different_keys_create_two_rows` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实执行验证 Run（由调度器后续接）；
- 双变量组合实验；
- 实验结果自动回写归因（TA-026 缺陷闭环）。
