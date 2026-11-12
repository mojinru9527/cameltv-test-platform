# Batch 315 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 强杀受控失败 | ✅ | `test_worker_kill_controlled_failure` |
| A2 | 恢复幂等 | ✅ | `test_recovery_is_idempotent` |
| A3 | 终态不变 | ✅ | `test_terminal_run_untouched` |
| A4 | 未知 Run | ✅ | `test_unknown_run_rejected` |
| A5 | 幂等变更 | ✅ | `test_idempotent_mutation_executes_once` |
| A6 | 不同 key | ✅ | `test_different_keys_execute_twice` |
| A7 | RBAC 审计 | ✅ | `test_permission_denied_is_audited` |
| A8 | 全量 + ratchet | ✅ | 1632 passed / 43 skipped；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | `transition()` 误用（实际为纯函数） | 改用 `apply_transition()` |
| 2 | RUF022 `__all__` 排序 / F401 | 排序 + 删未用 import |

## 判定

A1–A8 全绿，建议 Leader APPROVED。
