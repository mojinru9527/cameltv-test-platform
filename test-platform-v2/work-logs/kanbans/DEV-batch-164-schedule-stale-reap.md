# DEV-batch-164-schedule-stale-reap 看板

> 批次: batch-164-schedule-stale-reap | Executor: codex | 状态: 待总确认

## Slice
| # | Slice | 状态 |
|---|-------|------|
| S0 | worktree + PRD/PM/Design | ✅ |
| S1 | Schema + 模型 + 迁移（heartbeat_at） | ✅ |
| S2 | 心跳 + 回收 watchdog | ✅ |
| S3 | 回归测试 4 个 + 硬门禁（ruff ✅ pytest 1393 ✅ alembic ✅） | ✅ |
| S4 | QA + Leader + C163-1 关闭 + 合入 + 生产复验 | ⏳ |
