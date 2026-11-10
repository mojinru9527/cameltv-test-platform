# 🗂️ 看板：Batch 285（MinIO Artifact 存储）

| 字段 | 值 |
|------|-----|
| 批次 | batch-285（完整，M1 遗留） |
| 分支 | feature/batch-285-artifact-minio |
| 基线 | origin/main `79cbbbc11` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | MinIO 后端 + SigV4 | ✅ |
| 2 | 配置/工厂/URI 路由 | ✅ |
| 3 | compose minio | ✅ |
| 4 | 测试 5 | ✅ |
| 5 | 全量 1434 / ratchet | ✅ |
| 6 | PR / checks / merge | 🔄 |
| 7 | 生产 MinIO 部署 + 冒烟 | ⏳ |

## 下一步

- 生产 MinIO 容器 + env + ensure_bucket；
- M2 顺序：TA-011 RunContext。
