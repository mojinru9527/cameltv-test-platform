# Batch 310（M5 / TA-030）— A6 Learning Curator：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-310-m5-learning-curator · **基线**：origin/main `7c99056f5`
> **里程碑**：M5 第 2 批

## 1. 问题

学习候选规则若直接发布，会带来误报与重复规则。TA-030 要求：候选 → benchmark 评估 →
人审 → ACTIVE；**误报/重复增加不能无提示发布**。

## 2. 目标

1. 表 `learning_candidates` / `bug_patterns`（迁移 `20261122`）；
2. `evaluate_candidate`：benchmark 必须含 `false_positive_rate(0..1)` 与 `sample_size>0`；
3. `approve_candidate`：未 benchmark 拒绝；误报率 >20% 拒绝；重复候选需显式确认；
4. `activate_candidate`：approved → ACTIVE；重复/已存在 pattern 合并，不新增重复规则；
5. 列表查询。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 创建/校验 | `test_create_and_validate` |
| A2 | benchmark 状态 | `test_benchmark_sets_status` |
| A3 | 非法 benchmark | `test_invalid_benchmark_rejected` |
| A4 | 未 benchmark 不得批准 | `test_approve_requires_benchmark` |
| A5 | 高误报拒绝 | `test_high_false_positive_rejected` |
| A6 | 重复需确认 | `test_duplicate_requires_acknowledgement` |
| A7 | 激活创建 ACTIVE | `test_activate_creates_active_pattern` |
| A8 | 重复合并 | `test_duplicate_activation_merges_without_new_pattern` / `test_same_pattern_key_merges` |
| A9 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 benchmark 数据集执行（调用方传指标）；
- 规则生命周期 UI。
