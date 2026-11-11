# Batch 299 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 10 类命中 | ✅ | `test_each_kind_detected` |
| A2 | 干净无信号 | ✅ | `test_clean_payload_has_no_signals` |
| A3 | 极端 critical | ✅ | `test_critical_severity_for_extremes` |
| A4 | 多信号顺序 | ✅ | `test_multiple_signals_and_order` |
| A5 | 纯函数/确定性 | ✅ | `test_detection_is_pure_and_deterministic` |
| A6 | 不改 Run | ✅ | `test_detection_does_not_touch_run_state` |
| A7 | 非法输入 | ✅ | `test_invalid_payload_rejected` |
| A8 | 全量 + ratchet | ✅ | 1546 passed / 43 skipped；PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet UP035（typing.Callable） | 改 `collections.abc.Callable` |

## 风险

- 真实节点采集器未接（payload 契约已定）；
- 信号未持久化（后续 observations 表）。

## 判定

A1–A8 全绿，建议 Leader APPROVED。
