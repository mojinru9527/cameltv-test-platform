# 🗂️ 看板：Batch 277b-5 — P0-4 镜像验证

| 项 | 值 |
|----|-----|
| 批次 | batch-277b-5（light fix） |
| 分支 | fix/batch-277b-5-image-verify |
| 基线 | origin/main `46bea75bb` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | Dockerfile RUN 语法修复 | ✅ |
| 2 | 镜像构建（b277b4） | ✅ 812MB |
| 3 | 无 Chromium 验证 | ✅ find 无输出 |
| 4 | ENV 验证（browser=false / mode=node） | ✅ |
| 5 | P0-4 evidence JSON | ✅ pass（本地） |
| 6 | 守卫 P0-4 转绿 | ✅ |
| 7 | PR / checks / merge | 🔄 |

## 下一步

生产窗口：重建镜像 → digest 复核 → 部署（104 表 DROP）→ 真机 `/uitest` → P0-4 生产 digest 回填。
