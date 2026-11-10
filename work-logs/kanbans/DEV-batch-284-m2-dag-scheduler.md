# 🗂️ 看板：Batch 284（M2 / TA-010 + TA-010.3）

| 字段 | 值 |
|------|-----|
| 批次 | batch-284（完整，M2 第 2 批） |
| 分支 | feature/batch-284-m2-dag-scheduler |
| 基线 | origin/main `e2203b77c` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | WorkflowDefinition / ResourceLock | ✅ |
| 2 | workflow_service（审批冻结） | ✅ |
| 3 | resource_lock（TTL/fencing） | ✅ |
| 4 | dag_scheduler（推进/并行/阻断/收口/恢复） | ✅ |
| 5 | 迁移 20261114 | ✅ |
| 6 | 单测 15 | ✅ |
| 7 | 全量 1429 / ratchet | ✅ |
| 8 | 六件套 + 遗留登记 | ✅ |
| 9 | PR / checks / merge | 🔄 |

## 下一步

- M2 窗口部署（20261114 两表）；
- 遗留项：见 `work-logs/M1-M2-leftovers.md`；
- M2 后续：TA-011 RunContext、TA-012 HTTP Driver、TA-013 Playwright Driver。
