# 🗂️ 看板：Batch 277b-4 — 控制面无浏览器开关

| 项 | 值 |
|----|-----|
| 批次 | batch-277b-4（light） |
| 分支 | feature/batch-277b-4-browserless-control-plane |
| 基线 | origin/main `313eaa1f1` |

## 进度

| # | 项 | 状态 |
|---|----|:----:|
| 1 | `control_plane_browser_enabled` 开关 | ✅ |
| 2 | `/uitest` local 降级 | ✅ |
| 3 | `playwright_executor` 降级 | ✅ |
| 4 | XHR 采集 503 | ✅ |
| 5 | 蓝湖截图 error | ✅ |
| 6 | Playground 503 | ✅ |
| 7 | Dockerfile 去 Chromium + ENV | ✅ |
| 8 | 单测 7 + 回归 12 | ✅ |
| 9 | 镜像构建/inspect | ⏳ 网络受限 |
| 10 | 真机节点复验 + evidence | ⏳ 发布窗口 |

## 下一步

发布窗口：构建镜像 → 无 Chromium 验证 → 部署（含 104 表 DROP）→ 真机 `/uitest` → P0-4 证据。
