# Batch 305 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 回归记录 | ✅ | `test_create_regression_records_runs` |
| A2 | pending | ✅ | `test_pending_regression_without_verification_run` |
| A3 | 缺陷/SHA 校验 | ✅ | `test_unknown_defect_rejected` / `test_short_sha_rejected` |
| A4 | 四分类对比 | ✅ | `test_compare_runs_fixed_regressed_failing` |
| A5 | 旧 Run 不变 | ✅ | `test_compare_does_not_mutate_previous` |
| A6 | 多次回归 | ✅ | `test_regression_rows_persisted_per_attempt` |
| A7 | 前端组件 | ✅ | `RegressionComponents.test.tsx`（4） |
| A8 | 路由基线 | ✅ | 323 |
| A9 | 全量/质量 | ✅ | backend 1584 passed / 43 skipped；frontend 556 passed；typecheck/build；ratchet PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet UP045/UP037/UP017 | 新代码改 `X | None`、去引号、UTC |
| 2 | 前端全量偶发 `UiRunDetail` 超时 | 单跑/重跑通过（非本批改动，属 flaky） |

## 判定

A1–A9 全绿，建议 Leader APPROVED。
