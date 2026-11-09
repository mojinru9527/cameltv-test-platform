# 🗂️ 看板：Batch 277b-6 — 生产部署（P0 清零）

| 项 | 值 |
|----|-----|
| 批次 | batch-277b-6（light release） |
| 分支 | fix/batch-277b-6-prod-deploy |
| 基线 | origin/main `1109d0b74` |
| 生产 | swiftbugs.cn（111.230.155.116） |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | 补 start-worker.sh | ✅ |
| 2 | 部署前备份 | ✅ 168MB / sha256 `edff0f09…` |
| 3 | 镜像构建（无 Chromium） | ✅ sha256:23c02e88… |
| 4 | 首次部署（迁移失败） | ❌ → 回滚 200 |
| 5 | CASCADE 修复 | ✅ |
| 6 | 重新部署 | ✅ head `20261110…` / 94 表 |
| 7 | AI Key 注入 + provider 更新 | ✅ 真实调用 OK |
| 8 | 生产 `/uitest` 节点 E2E | ✅ run 481 / 1/1 |
| 9 | ai-gateway 退役 | ✅ |
| 10 | 磁盘 77% | ✅ |
| 11 | 守卫 5/5 | ✅ PASS |
| 12 | PR #507 合入 | 🔄 |

## 下一步

M1 batch-279（TA-005 Run/Event/Artifact）；浏览器依赖迁移批次；compose 同步。
