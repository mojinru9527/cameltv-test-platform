# Batch 287 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 链式成功 + 证据 | ✅ | `test_chain_success_records_evidence` |
| A2 | 首失败即停 + 历史保留 | ✅ | `test_chain_stops_at_first_failure_and_preserves_result` |
| A3 | 敏感头脱敏 | ✅ | `test_sensitive_headers_redacted` |
| A4 | 超时映射 | ✅ | `test_timeout_maps_to_error` |
| A5 | body 截断 | ✅ | `test_body_truncated` |
| A6 | content 哈希 | ✅ | `test_content_evidence_has_hash` |
| A7 | 全量 + ratchet | ✅ | 1449 passed / 43 skipped；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | 测试对 JSON 空格/Header 大小写过严 | 按语义断言 |
| 2 | 本机 openpyxl `.pyc` 损坏导致导入失败 | 清理 `__pycache__` 后恢复 |

## 判定

A1–A7 全绿，建议 Leader APPROVED。
