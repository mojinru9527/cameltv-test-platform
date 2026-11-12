# Batch 315 — Design / Dev

## 接口

```python
recover_after_worker_kill(db, run_id, reason="worker killed") -> {
  run_id, recovered, status, outcome, blocked_nodes
}
run_idempotent_mutation(db, key, mutation) -> (result, executed)
audit_permission_denied(db, user_id, username, project_id, action, target, ip="")
```

## 状态处理

| 当前状态 | 恢复动作 |
|----------|----------|
| RUNNING | COMPLETED + INCOMPLETE |
| QUEUED/VALIDATING/WAITING_HUMAN/TRIAGING | ERROR |
| 终态 | 不变（recovered=False） |

节点：PENDING/READY/RUNNING → BLOCKED，error_class=WORKER_LOST。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-315-1 | 强杀=INCOMPLETE 而非 ERROR | 保留“部分执行”事实 |
| D-315-2 | 幂等账本独立表 | 支付/造数共用 |
| D-315-3 | 恢复只处理非终态 | 防覆盖已完成结果 |
| D-315-4 | 审计 detail 固定 | 可检索权限拒绝 |

## 文件

- `app/aiqe/models/hardening.py`、`app/aiqe/services/hardening_service.py`
- `alembic/versions/20261123_ta033_mutation_ledger.py`
- `tests/test_aiqe_hardening.py`（7 条）
