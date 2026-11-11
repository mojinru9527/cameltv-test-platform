# Batch 293 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 依赖 + 脱敏 + argv | ✅ | `test_record_dependency_and_redaction` |
| A2 | 无依赖拒绝 | ✅ | `test_record_without_dependencies_rejected` |
| A3 | 回放稳定 | ✅ | `test_replay_stable` |
| A4 | 回放不稳定 | ✅ | `test_replay_unstable_rejected` |
| A5 | 嵌套脱敏 | ✅ | `test_redact_payload_nested` |
| A6 | eBPF 审计 | ✅ | `test_audit_ebpf_fields` |
| A7 | 权限不足 | ✅ | `test_assert_ebpf_ready_rejects_non_linux` |
| A8 | 报告缺失 | ✅ | `test_missing_report_raises` |
| A9 | 全量 + ratchet | ✅ | 1502 passed / 43 skipped；PASS |

## 缺陷

无（8/8 首轮通过）。

## 风险

- 真实 Keploy/eBPF 未执行（mock 报告）；
- 依赖图谱/深度 diff 后续。

## 判定

A1–A9 全绿，建议 Leader APPROVED。
