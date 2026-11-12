# Batch 315（M6 / TA-033）— Reliability + Security Hardening：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-315-m6-hardening · **基线**：origin/main `04526b61b`
> **里程碑**：**M6 第 1 批**

## 1. 问题

Worker 被强杀后 Run 可能永久 RUNNING；重试/扣款/造数若无幂等会产生重复副作用；RBAC 拒绝若
不审计则无法追责。

## 2. 目标

1. `recover_after_worker_kill()`：RUNNING → `COMPLETED/INCOMPLETE`，未完成节点 `BLOCKED`，
   重复恢复幂等；其它非终态 → `ERROR`；
2. `mutation_ledger` 幂等账本：同 key 只执行一次（防重复扣款/造数）；
3. `audit_permission_denied()`：权限拒绝写审计（detail=permission_denied）；
4. 迁移 `20261123`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 强杀受控失败 | `test_worker_kill_controlled_failure` |
| A2 | 恢复幂等 | `test_recovery_is_idempotent` |
| A3 | 终态不变 | `test_terminal_run_untouched` |
| A4 | 未知 Run | `test_unknown_run_rejected` |
| A5 | 幂等变更一次 | `test_idempotent_mutation_executes_once` |
| A6 | 不同 key 各一次 | `test_different_keys_execute_twice` |
| A7 | RBAC 拒绝审计 | `test_permission_denied_is_audited` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实压测/故障注入集群（服务层已固化语义）；
- 支付对账系统（幂等账本先兜底）。
