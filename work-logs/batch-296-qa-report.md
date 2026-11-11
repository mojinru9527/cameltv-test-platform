# Batch 296 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 合法规划 pending | ✅ | `test_valid_plan_is_pending` |
| A2 | 自批拒绝 | ✅ | `test_self_approval_rejected` |
| A3 | 环拒绝 | ✅ | `test_cycle_rejected` |
| A4 | 未注册 driver | ✅ | `test_unknown_driver_rejected` |
| A5 | 依赖比对 | ✅ | `test_dependencies_match` |
| A6 | 未批准不可执行 | ✅ | `test_unapproved_cannot_execute` |
| A7 | 20 标注工作流 | ✅ | `test_twenty_labeled_workflows` |
| A8 | 全量 + ratchet | ✅ | 1522 passed / 43 skipped；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | 测试里残留无效 `with raises` 块 | 删除 |

## 风险

- 真实 LLM 未接；
- 条件边/审批 UI 未做。

## 判定

A1–A8 全绿，建议 Leader APPROVED。
