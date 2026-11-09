# Batch 283（M2 / TA-009）— Workflow Validator：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整
> **分支**：feature/batch-283-m2-workflow-validator · **基线**：origin/main `ae13542a3`
> **里程碑**：M2 第 1 批

## 1. 问题

M1 有 Run/Event/Artifact，但还没有 Workflow 定义的准入：错误 DAG（环、悬空依赖、
悬空变量、非幂等重试）会在执行期才炸，污染 Run 事实源。TA-009 要在入库前 fail-closed。

## 2. 目标

`validate_workflow(graph, registered_drivers, registered_capabilities)`：

1. schema_version 必须存在；node key 唯一；depends_on 指向存在节点；无环；
2. edges 与 depends_on 一致；
3. driver / capability 必须已注册；
4. `${nodes.X.outputs.Y}` 中 X 必须是当前节点的**传递祖先**且 Y 已声明；
5. assertion 必须有 `expected`/`expected_ref`（`type=exploratory` 除外）；
6. 写操作（POST/PUT/PATCH/DELETE 或 cleanup）`max_attempts>1` 必须有
   `idempotency_key_expr` 或 `compensation_node`；
7. 提供 canonical `workflow_checksum()`（规则 7 基础）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 合法样例通过 | `test_valid_sample_passes` |
| A2 | 环 / 悬空依赖 / 重复 key 拒绝 | `test_dependency_cycle` 等 |
| A3 | 未注册 driver/capability 拒绝 | `test_unregistered_*` |
| A4 | 悬空变量 / 非祖先 / 未声明输出拒绝 | `test_variable_*` |
| A5 | 非幂等写重试拒绝（带 idempotency 放行） | `test_non_idempotent_write_retry_*` |
| A6 | assertion expected / exploratory | `test_assertion_*` |
| A7 | edge 一致性 + checksum 稳定 | `test_edge_*` / `test_checksum_*` |
| A8 | 全量回归 + ratchet | CI |

## 4. 非目标

- Workflow 存储表/API（TA-010 调度器一起做）；
- 规则 6（DB/网络/设备写动作 profile policy）留 TA-010；
- checksum 审批流（M2 后续）。
