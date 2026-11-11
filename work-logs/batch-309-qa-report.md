# Batch 309 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | auth 强制 | ✅ | `test_auth_change_forces_auth_and_smoke` |
| A2 | 多域并集 | ✅ | `test_union_of_multiple_areas` |
| A3 | 未知 smoke | ✅ | `test_unknown_change_defaults_to_smoke` |
| A4 | 合法输出 | ✅ | `test_valid_agent_output` |
| A5 | 漏强制 suite | ✅ | `test_omitted_forced_suite_rejected` |
| A6 | 漏 auth 域 | ✅ | `test_omitted_auth_area_rejected` |
| A7 | 空 diff | ✅ | `test_empty_files_rejected` |
| A8 | 全量 + ratchet | ✅ | 1599 passed / 43 skipped；PASS |

## 判定

A1–A8 全绿，建议 Leader APPROVED。
