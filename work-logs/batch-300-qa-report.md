# Batch 300 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 合法归因 | ✅ | `test_valid_attribution` |
| A2 | 自动关缺陷拒绝 | ✅ | `test_auto_close_rejected` |
| A3 | confidence 非 null | ✅ | `test_confidence_must_be_null` |
| A4 | 人工复核必需 | ✅ | `test_human_review_required` |
| A5 | UNKNOWN 一致性 | ✅ | `test_unknown_requires_unknown_status` |
| A6 | CROSS_FEATURE 证据 | ✅ | `test_cross_feature_requires_evidence` |
| A7 | 空假设 | ✅ | `test_empty_hypotheses_rejected` |
| A8 | 100 标注样本 | ✅ | `test_hundred_labeled_samples`（12 类覆盖） |
| A9 | 全量 + ratchet | ✅ | 1554 passed / 43 skipped；PASS |

## 缺陷

无（8/8 首轮通过）。

## 风险

- 合成 100 样本，真实 §21.4 标注集未接入；
- 归因未入库（triage_cases 后续）。

## 判定

A1–A9 全绿，建议 Leader APPROVED。
