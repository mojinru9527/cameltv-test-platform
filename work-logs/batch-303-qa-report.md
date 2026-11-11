# Batch 303 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | E1-E6 落 verification_run_id | ✅ | `test_each_experiment_records_verification_run` |
| A2 | 双变量拒绝 | ✅ | `test_double_variable_rejected` |
| A3 | 空变更拒绝 | ✅ | `test_empty_change_rejected` |
| A4 | 未知实验拒绝 | ✅ | `test_unknown_experiment_rejected` |
| A5 | 幂等同记录 | ✅ | `test_idempotency_returns_same_record` |
| A6 | 显式 verification_run | ✅ | `test_explicit_verification_run_preserved` |
| A7 | 不同 key 两行 | ✅ | `test_different_keys_create_two_rows` |
| A8 | 迁移/全量/ratchet | ✅ | up/down/up 0/0/0；1569 passed；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet F401（Integer） | 删除未用 import |

## 判定

A1–A8 全绿，建议 Leader APPROVED。
