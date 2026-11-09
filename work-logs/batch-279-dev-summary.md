# Batch 279（M1 / TA-005）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 变更文件

| 文件 | 说明 |
|------|------|
| `backend/app/aiqe/__init__.py` | AIQE 领域包 |
| `backend/app/aiqe/models/run.py` | TestRun / NodeRun / StepAttempt / RunAssertionResult |
| `backend/app/aiqe/models/__init__.py` | 模型导出 |
| `backend/app/aiqe/services/run_state.py` | 状态机唯一入口 + 异常 |
| `backend/app/models/__init__.py` | 注册 aiqe 模型到 `Base.metadata` |
| `backend/alembic/versions/20261111_ta005_run_models.py` | 四表迁移（up/down） |
| `backend/tests/test_aiqe_run_state.py` | 状态机 31 条参数化用例 |
| `backend/tests/test_aiqe_run_models.py` | ORM 约束/关联 6 条 |

## 行为

- `transition(current, target, outcome=...)`：合法返回 target；非法抛
  `InvalidStateTransition`；`COMPLETED` 缺 outcome、终态带 outcome 均拒绝。
- `apply_transition(run, target, outcome=...)`：改 `run.status/outcome`，不 commit。
- `NodeRun.execution_job_id` 可直接填既有 `ExecutionJob.id`；删除 Job 时 SET NULL。
- 删除 Run 级联删除 node_runs → step_attempts → run_assertion_results。
- `attempt_no` 唯一约束保证“重跑追加、不覆盖”。

## 本地验证

```text
pytest tests/test_aiqe_run_state.py tests/test_aiqe_run_models.py  → 37 passed
alembic upgrade head                                              → OK
alembic downgrade -1                                              → OK
alembic upgrade head                                              → OK
quality_ratchet.py                                                → PASS (increased_keys=0)
```

## 兼容性

- 不修改任何现有表/接口；
- 新模型只在 `Base.metadata` 注册，不影响现有启动路径；
- 迁移在无 M1 表的库（生产）创建，在已预建的库（SQLite 新库）跳过。
