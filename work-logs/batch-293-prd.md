# Batch 293（M3 / TA-018）— Keploy Record/Replay PoC：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-293-m3-keploy-adapter · **基线**：origin/main `28e6d86cf`
> **里程碑**：M3 第 3 批

## 1. 问题

Keploy 依赖 eBPF/root，录制内容含鉴权头，回放可能不稳定。直接接入会带来权限、脱敏、
结果不可复现三类风险。TA-018 用 PoC 固化：依赖捕获、回放稳定性、脱敏、eBPF 审计。

## 2. 目标

1. `record`：要求至少捕获 **1 条上下游依赖**，否则拒绝；
2. `replay(times=2)`：连续回放，`passed/failed` 不一致 → `KeployReplayUnstable`；
3. 脱敏：`authorization/cookie/token/password/secret…` 全部 `***`（含嵌套）；
4. `audit_ebpf()`：Linux + (root 或 CAP_BPF) 才允许真实执行；非 Linux/无权限拒绝；
5. 报告缺失/非法 JSON → `KeployError`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 依赖捕获 + 脱敏 + argv | `test_record_dependency_and_redaction` |
| A2 | 无依赖拒绝 | `test_record_without_dependencies_rejected` |
| A3 | 回放稳定 | `test_replay_stable` |
| A4 | 回放不稳定拒绝 | `test_replay_unstable_rejected` |
| A5 | 嵌套脱敏 | `test_redact_payload_nested` |
| A6 | eBPF 审计 | `test_audit_ebpf_fields` |
| A7 | 权限不足拒绝 | `test_assert_ebpf_ready_rejects_non_linux` |
| A8 | 报告缺失 | `test_missing_report_raises` |
| A9 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 Keploy 二进制/eBPF 录制（PoC 用 mock 报告，权限门禁先落地）；
- 依赖图谱建模（只捕获原始依赖条目）；
- CI 调度接入。
