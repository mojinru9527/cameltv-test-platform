# Batch 298（M3 / TA-022）— Execution Profile / 数据隔离：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-298-m3-execution-profile · **基线**：origin/main `b620e0520`
> **里程碑**：M3 第 7 批

## 1. 问题

同一份共享 fixture 被两个并发 Run 修改会互相污染；`external_live` 环境更不允许写共享数据。
此前没有 profile 概念与隔离约束。

## 2. 目标

1. `execution_profiles` 表（§4.13）与三档 `purpose`：`core_isolated / integration / external_live`；
2. checksum = canonical JSON(purpose+name+version+config) sha256，**可复现**；
3. `core_isolated` → Run 级 namespace `iso-<run_id>`；`integration` → `integration`；`external_live` → `live`；
4. `external_live` 写共享 fixture → fail-closed；
5. `fixture:<key>` 资源锁：两个并发 Run 不能同时写同一 fixture；
6. approved profile 不可改（只能新建 version）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | purpose 校验 | `test_unknown_purpose_rejected` |
| A2 | checksum 可复现 | `test_checksum_reproducible_and_content_sensitive` |
| A3 | 三档 namespace | `test_namespaces` |
| A4 | external_live 禁写 | `test_external_live_rejects_fixture_mutation` |
| A5 | 并发 Run 互斥 | `test_two_runs_cannot_share_fixture` |
| A6 | approved 冻结 | `test_approved_profile_immutable` |
| A7 | core_isolated Run 级隔离 | `test_core_isolated_starts_with_run_namespace` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 Test 环境 adapter（TA-003 后续）；
- profile 审批 UI；
- fixture 清理/回滚协议（M4）。
