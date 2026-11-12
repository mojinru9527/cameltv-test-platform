# 🗂️ 看板：Batch 329（P0 收口）

| 字段 | 值 |
|------|-----|
| 批次 | batch-329（完整） |
| 分支 | feature/batch-329-p0-closeout |
| 基线 | origin/main `45f4bb7e2` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | NodeRun→ExecutionJob 桥接 | ✅ |
| 2 | 条件边 success/failure/always | ✅ |
| 3 | Artifact 30 天 GC | ✅ |
| 4 | Dogfood M1–M8 留档（339 passed） | ✅ |
| 5 | TC-AIQE E2E 入口 | ✅（env-gated） |
| 6 | 全量 + ratchet | 🔄 |
| 7 | PR / checks / merge | 🔄 |
| 8 | 生产 release-m9 | ⏳ |

## 剩余（环境/后续批次）

真实 TC-AIQE 执行、第二项目实机、P1 Console/SSE、P2 真实设备。
