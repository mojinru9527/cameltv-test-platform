# Batch 329（P0 收口）— 调度桥接 / 条件边 / Artifact GC / Dogfood：PRD

> **模式**：完整 · **分支**：feature/batch-329-p0-closeout · **基线**：`45f4bb7e2`

## 目标（P0 代码项）

1. `execution_dispatcher`：NodeRun → 既有 ExecutionJob/Worker 队列，幂等（同一 node 不重复建 Job）；
2. 条件边：`edges.condition ∈ {success, failure, always}` 驱动 READY；
3. Artifact 30 天 GC：DB + 文件（Local/MinIO delete）；
4. Dogfood Ratchet 执行器：M1–M8 + P0 子集留档（真实 pytest 结果）；
5. TC-AIQE-001..010 E2E 入口：隔离环境 Playwright，未配置时 skip，不造假绿。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | dispatch 落 Job | `test_dispatch_creates_linked_job` |
| A2 | dispatch 幂等 | `test_dispatch_is_idempotent` |
| A3 | 条件边 failure/always | `test_failure_edge_fires_only_on_failure` |
| A4 | success 不触发 failure 边 | `test_failure_edge_does_not_fire_on_success` |
| A5 | GC 删除过期 | `test_gc_removes_expired_artifact` |
| A6 | GC 保留近期/失败保留记录 | `test_gc_keeps_recent_artifact` / `test_gc_storage_failure_keeps_row` |
| A7 | Dogfood 留档 | `work-logs/aiqe/dogfood/M*.md`（339 passed） |
| A8 | E2E 入口 | `tests/e2e/aiqe/test_tc_aiqe_001_010.py`（env-gated） |
| A9 | 全量 + ratchet | CI |

## 非目标

- 真实隔离环境执行 TC-AIQE（需 Test 环境账号，代码入口已备）；
- P1/P2（Console/RBAC/SSE/真实设备）另批。
