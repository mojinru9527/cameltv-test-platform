# Batch 284（M2 / TA-010 + TA-010.3）— DAG Scheduler + 资源锁：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整
> **分支**：feature/batch-284-m2-dag-scheduler · **基线**：origin/main `e2203b77c`
> **里程碑**：M2 第 2 批（依赖 batch-283 校验器 + M1 Run/NodeRun）

## 1. 问题

Workflow 能校验，但还不能实例化执行：没有 NodeRun 生成、依赖推进、并行上限、失败阻断、
资源互斥与 Worker 重启恢复。

## 2. 目标

1. **Workflow 定义存储**：`workflow_definitions`（§4.6），approved 后 graph/checksum 冻结；
2. **DAG 调度**：按 depends_on 生成 NodeRun、READY 推进、`max_parallel_nodes` 限制、
   fail_fast / 依赖传播阻断、cleanup 节点终态触发、Run 收口（PASS/FAIL/INCOMPLETE）；
3. **资源锁**（TA-010.3）：7 粒度 key、TTL、heartbeat、单调 fencing token；
4. **恢复**：Worker 重启后 RUNNING 且锁失效的节点回到调度；
5. 迁移 `20261114`（两表）+ 单测。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 串行→并行→汇聚 | `test_serial_parallel_join_and_complete` |
| A2 | 并行上限生效 | `test_parallel_limit_one` |
| A3 | fail_fast 阻断 Run（BLOCKED，无 outcome） | `test_fail_fast_blocks_run` |
| A4 | 资源锁互斥 + 释放后可调度 | `test_resource_lock_blocks_second_run` |
| A5 | Worker 重启恢复 | `test_recover_resumes_running_node` |
| A6 | cleanup 节点 + Run PASS | `test_cleanup_node_runs_after_terminal` |
| A7 | 锁 TTL/fencing/续租 | `test_aiqe_resource_lock.py` 5 条 |
| A8 | Workflow 审批冻结 | `test_aiqe_workflow_service.py` 4 条 |
| A9 | 全量回归 + ratchet | CI |

## 4. 非目标

- 真正执行节点（dispatch 只回调；接 execution_jobs 在 TA-012+）；
- 条件分支完整语义（只支持 depends_on 成功边；`edges.condition` 后续）；
- 规则 6 的 profile policy（需 `execution_profiles` 表，TA-010 后续）；
- capability 注册表（TA-015）。
