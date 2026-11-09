# 🗂️ 看板：Batch 280（M1 / TA-006 Event + Outbox）

| 字段 | 值 |
|------|-----|
| 批次 | batch-280（完整） |
| 分支 | feature/batch-280-m1-event-outbox |
| 基线 | origin/main `10c0f9213` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | run_events / event_outbox 模型 | ✅ |
| 2 | append_event（幂等/锁/同事务/投影） | ✅ |
| 3 | list_events / dispatch_outbox | ✅ |
| 4 | 迁移 20261112（预建跳过） | ✅ |
| 5 | 单测 10（含 1000 事件） | ✅ |
| 6 | 全量 1386 passed / ratchet | ✅ |
| 7 | 六件套 + 本看板 | ✅ |
| 8 | PR / checks / merge | 🔄 |

## 下一步

batch-281（TA-007 Artifact Manager）：`run_artifacts` + 本地 FS 后端 + sha256 去重 + 越权 403。
