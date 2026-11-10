# Batch 284（M2 / TA-010）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 文件

| 文件 | 说明 |
|------|------|
| `app/aiqe/models/workflow.py` | WorkflowDefinition / ResourceLock |
| `app/aiqe/services/workflow_service.py` | 创建/审批/冻结/改图 |
| `app/aiqe/services/resource_lock.py` | acquire/renew/release/reap + fencing |
| `app/aiqe/services/dag_scheduler.py` | create/schedule/complete/recover |
| `alembic/versions/20261114_ta010_workflow_scheduler.py` | 两表迁移 |
| `tests/test_aiqe_{resource_lock,workflow_service,dag_scheduler}.py` | 15 条单测 |

## 行为

- 菱形图 A→(B,C)→D：A 先 READY，A 完成后 B/C 并行，B/C 完成后 D，最终 Run PASS；
- `max_parallel_nodes=1` 时严格串行；
- fail_fast 失败 → Run BLOCKED、未终态节点 BLOCKED；
- 两个 Run 争同一 resource key：第二个保持 PENDING，释放后下一轮 READY；
- Worker 重启：RUNNING 且锁失效 → PENDING → 重新 dispatch；
- cleanup 节点在所有非 cleanup 终态后执行，完成后 Run 收口。

## 验证

```text
pytest tests/test_aiqe_resource_lock.py tests/test_aiqe_workflow_service.py tests/test_aiqe_dag_scheduler.py → 15 passed
pytest -q        → 1429 passed / 43 skipped
alembic up/down/up → 0/0/0
ratchet          → PASS
```
