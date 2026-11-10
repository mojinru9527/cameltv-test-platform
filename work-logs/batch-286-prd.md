# Batch 286（M2 / TA-011）— RunContext / Variable Store：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-286-m2-run-context · **基线**：origin/main `7f3843ea1`

## 1. 问题

DAG 节点之间需要传变量（如 `match_id`），但没有统一规则：引用易悬空、secret 可能被写进
日志/Artifact，跨 Run 可能串数据。TA-011 要在执行期提供受控变量解析。

## 2. 目标

1. `RunContext`：`${nodes.X.outputs.Y}` 解析同一 Run 已执行节点 `output_ref`；
2. `${secrets.NAME}` 仅在执行期从注入 mapping 解析，**不落库**；
3. `snapshot()` 对 secret 引用与已知 secret 值脱敏；
4. `set_output()` 拒绝写入 `${secrets.*}`（fail-closed）；
5. 调度器 `complete_node(outputs=...)` 写入 `node_runs.output_ref`；
6. Run scope 隔离（同 node_key 不同 Run 不串）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 类型保真解析（int/dict） | `test_resolve_typed_and_nested` |
| A2 | 字符串插值 | `test_string_interpolation` |
| A3 | 悬空节点/输出/命名空间报错 | `test_missing_references` |
| A4 | secret 解析 + 未注入报错 | `test_secrets_resolution_and_errors` |
| A5 | 输出拒绝 secret 引用 | `test_set_output_rejects_secret_ref` |
| A6 | snapshot 脱敏 | `test_snapshot_redacts_secrets` |
| A7 | Run 隔离 | `test_run_scope_isolation` |
| A8 | 调度器输出写入 + 引用 | `test_scheduler_writes_outputs` |
| A9 | 全量 + ratchet | CI |

## 4. 非目标

- Vault/KMS 集成（secret 由调用方注入 mapping）；
- 跨 Run 继承/重放变量（M3）；
- 变量 schema 校验（TA-009 已管 graph 级）。
