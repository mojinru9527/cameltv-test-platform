# 🗂️ 看板：Batch 340（attempt 持久化 + 重试）

| 字段 | 值 |
|------|-----|
| 批次 | batch-340（full） |
| 分支 | feature/batch-340-attempts-retry |
| 基线 | origin/main `7fb0af008` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | StepAttempt 写入/收口 | ✅ |
| 2 | retry.max_attempts 策略 | ✅ |
| 3 | `GET /aiqe/runs/{id}/attempts` | ✅ |
| 4 | 路由基线同步 | ✅ |
| 5 | 后端测试 4 条 + DAG/Run 回归 12 条 | ✅ |
| 6 | 全量回归 / PR / checks / 合入 | 🔄 |
| 7 | Test 执行引擎启用 + 实机验证 | ⏳ |

## 下一步

- 合入后：Test 开 `WORKER_EXECUTION_ENABLED=true` 并用真实 Run 验证 attempt 时间线；
- batch-341：RegressionRequest API（解锁 TC-008）。
