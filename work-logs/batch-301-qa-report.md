# Batch 301 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 广告抖动 hint+证据 | ✅ | `test_ad_jitter_sample_with_evidence` |
| A2 | ≤3 条 hint | ✅ | `test_at_most_three_hints` |
| A3 | 空证据拒绝 | ✅ | `test_empty_evidence_rejected` |
| A4 | 非法前缀拒绝 | ✅ | `test_invalid_evidence_prefix_rejected` |
| A5 | 禁止自动关缺陷 | ✅ | `test_auto_close_rejected` |
| A6 | 人工复核 | ✅ | `test_human_review_required` |
| A7 | UNKNOWN 兜底 | ✅ | `test_unknown_factor_allowed` |
| A8 | 0 条拒绝 | ✅ | `test_zero_hints_rejected` |
| A9 | 全量 + ratchet | ✅ | 1562 passed / 43 skipped；PASS |

## 判定

A1–A9 全绿，建议 Leader APPROVED。
