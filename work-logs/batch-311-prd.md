# Batch 311（M5 / TA-031）— VersionTask Quality Gate：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-311-m5-quality-gate · **基线**：origin/main `e27e1f4dd`
> **里程碑**：M5 第 3 批

## 1. 问题

版本任务门禁若把“P0 未执行/未知”当成通过，会放行未验证版本。TA-031 要求：
**P0 未执行 / 未知 / 失败 → 门禁不显示 PASS**。

## 2. 目标

1. `evaluate_cases(cases)`：按 P0 用例状态判定；
2. `evaluate_stats(stats)`：按聚合计数判定；
3. 状态：
   - 有 P0 FAIL → `FAIL`；
   - P0 UNKNOWN/NOT_RUN → `BLOCKED`；
   - 无 P0 → `BLOCKED`；
   - 仅 P0 全 PASS → `PASS`；
4. 非 P0 状态不影响门禁，但保留统计。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 全 P0 PASS | `test_all_p0_pass` |
| A2 | P0 失败/未知/未执行均非 PASS | `test_p0_not_passed_blocks_gate`（3 组） |
| A3 | P0 FAIL → FAIL | `test_p0_fail_is_fail` |
| A4 | UNKNOWN/NOT_RUN → BLOCKED | `test_p0_unknown_or_not_run_is_blocked` |
| A5 | 无 P0 → BLOCKED | `test_no_p0_blocked` |
| A6 | 聚合统计 | `test_stats_gate` / `test_empty_stats_blocked` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 前端版本任务详情页改造（服务先固化判定）；
- 环境健康/覆盖率门禁组合。
