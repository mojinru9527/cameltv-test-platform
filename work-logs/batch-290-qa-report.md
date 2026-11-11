# Batch 290 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 无 evidence 不可用 | ✅ | `test_register_without_evidence_is_unavailable` |
| A2 | 有 evidence 支持能力 | ✅ | `test_register_with_evidence_and_supports` |
| A3 | 缺 WebKit 不选中 | ✅ | `test_node_without_webkit_not_selected` |
| A4 | 多能力全覆盖 | ✅ | `test_select_requires_all_capabilities` |
| A5 | upsert 单行 | ✅ | `test_upsert_updates_single_row` |
| A6 | evidence 翻转 available | ✅ | `test_record_evidence_flips_available` |
| A7 | 校验器接入 | ✅ | `test_known_capabilities_drive_validator` |
| A8 | 迁移 + 全量 + ratchet | ✅ | up/down/up 0/0/0；1478 passed；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet F401/UP035 | 删未用 import、改 collections.abc |

## 判定

A1–A8 全绿，建议 Leader APPROVED；**M2 收口**。
