# Batch 304 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 结构化草稿落库 | ✅ | `test_create_draft_with_structured_reproduction` |
| A2 | 缺 action/expected | ✅ | `test_missing_action_rejected` / `test_missing_expected_rejected` |
| A3 | 空步骤 | ✅ | `test_empty_steps_rejected` |
| A4 | 证据白名单 | ✅ | `test_empty_evidence_rejected` / `test_invalid_evidence_prefix_rejected` |
| A5 | AC 必需/格式 | ✅ | `test_ac_required_and_valid` |
| A6 | 幂等 | ✅ | `test_idempotent_same_run_and_title` |
| A7 | 详情页展示 | ✅ | `AiqaLinkSection.test.tsx`（2） |
| A8 | 全量/质量 | ✅ | backend 1577 passed / 43 skipped；frontend 552 passed；typecheck/build OK；ratchet PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | vitest 无 jest-dom matcher | 改用 `toBeTruthy` / `innerHTML` |
| 2 | ratchet UP045（Optional） | 新字段改 `X | None` |

## 判定

A1–A8 全绿，建议 Leader APPROVED。
