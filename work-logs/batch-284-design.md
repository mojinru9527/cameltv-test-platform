# Batch 284（M2 / TA-010）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 1. 调度状态机

```text
schedule(run, graph):
  run QUEUED → RUNNING
  循环：
    PENDING 且 deps 全 PASSED（cleanup 节点等所有非 cleanup 终态）
    + 活跃节点 < max_parallel_nodes
    + 资源锁 acquire 成功
      → READY，dispatched（回调交给执行层）
complete_node(status):
  终态持久化 → 释放资源锁
  FAILED 且 fail_fast → 全部未终态节点 BLOCKED，Run BLOCKED
  FAILED 非 fail_fast → 下游传播 BLOCKED
  全部终态 → Run COMPLETED（PASS / FAIL / INCOMPLETE）
recover():
  RUNNING 且锁行不存在/已过期/owner 不符 → PENDING → schedule 重派
```

## 2. 资源锁

- 行级锁 `resource_locks(key PK, owner_id, fencing_token, expires_at)`；
- acquire：无行 → fencing=1；过期/同 owner → 续租（换 owner 时 token+1）；否则 `LockUnavailable`；
- renew 需 token 匹配；release 只置过期并清空 owner（token 单调保留）；
- SQLite 时区 naive 问题已归一（`_as_utc`）。

## 3. Workflow 存储

`workflow_definitions`：`(scenario_id, version)` 唯一；`approve_workflow()` 冻结 graph/checksum；
`update_graph()` 对 approved 抛 `WorkflowImmutableError`；新建版本自动 +1。

## 4. 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-284-1 | 调度器不执行节点，只 dispatch 回调 | 执行层（ExecutionJob/Worker）解耦，测试可注入 |
| D-284-2 | fail_fast 时 Run 置 BLOCKED（无 outcome） | 符合“BLOCKED ≠ PASS” |
| D-284-3 | 非 fail_fast 失败向下游传播 BLOCKED，其余继续 | DAG 部分成功语义 |
| D-284-4 | release 不删行，置过期并保留 token | 保证 fencing 单调，避免 ABA |
| D-284-5 | cleanup 节点等所有非 cleanup 终态 | 与 §6.1 `depends_on_terminal` 对齐 |
| D-284-6 | 条件分支/规则 6 留后续 | 当前只支持成功边，避免过度设计 |
