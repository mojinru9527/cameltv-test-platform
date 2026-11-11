# Batch 306 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 默认 90 天 | ✅ | `test_default_expiry_is_90_days` |
| A2 | 永久 quarantine | ✅ | `test_permanent_quarantine_rejected` |
| A3 | 超 90 天 | ✅ | `test_expiry_over_90_days_rejected` |
| A4 | 到期失效 | ✅ | `test_expired_rule_not_effective` |
| A5 | 续期 | ✅ | `test_renew_extends_90_days` |
| A6 | 更新 | ✅ | `test_update_pattern_and_action` |
| A7 | 删除/非法 | ✅ | `test_delete_rule` / `test_invalid_action_and_empty_pattern` |
| A8 | 前端表格 | ✅ | `NoiseRuleTable.test.tsx`（2） |
| A9 | 全量 | ✅ | backend 1592 passed / 43 skipped；frontend 558 passed；typecheck/build；ratchet PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet RUF022 `__all__` 排序 | NodeRun 在前、NoiseRule 在后 |

## 判定

A1–A9 全绿，建议 Leader APPROVED。
