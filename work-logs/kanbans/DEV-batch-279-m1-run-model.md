# 🗂️ Dev 看板：Batch 279（M1 / TA-005）

| 字段 | 值 |
|------|-----|
| 项目 | M1：Run / Event / Artifact 底座 |
| 批次 | batch-279（完整批次） |
| Executor | DeepSeek Harness |
| 分支 | feature/batch-279-m1-run-model |
| 基线 | origin/main `16ebdbfb7` |
| 创建 | 2026-11-10 |

## 进度

| # | 项 | 状态 |
|---|----|:----:|
| 1 | 四表模型 + 关系 | ✅ |
| 2 | 状态机唯一入口 | ✅ |
| 3 | Alembic 迁移（up/down/预建跳过/遗留清理） | ✅ |
| 4 | 模型注册 | ✅ |
| 5 | 单测 37 | ✅ |
| 6 | 全量回归 1376 passed | ✅ |
| 7 | ratchet | ✅ |
| 8 | PR / checks / merge | 🔄 |
| 9 | 生产部署（M1 窗口） | ⏭ |

## 下一步

- 本批合入后启动 **batch-280（TA-006 Event Collector + Outbox）**；
- 生产窗口：`alembic upgrade head` 建四表并核对 `\dt test_runs`。
