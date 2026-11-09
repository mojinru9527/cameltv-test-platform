# Batch 277b-5 — P0-4 镜像验证：PRD-lite

> **部门**：🟦 Product（lite） · **日期**：2026-11-09 · **批次模式**：light（修复 + 证据）
> **分支**：fix/batch-277b-5-image-verify（基线 `46bea75bb`）

## 1. 问题

277b-4 合入后，Dockerfile 的 `RUN --mount ... && cd` 语法错误只在真实构建时暴露；同时 P0-4 缺"镜像无 Chromium"的可复核证据。

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| Dockerfile 可构建 | 1 | ✅（修复 RUN 语法） |
| 镜像无 Chromium | 0 命中 | ✅ `find` 无输出 |
| 镜像 ENV | 2 项 | ✅ `CONTROL_PLANE_BROWSER_ENABLED=false` / `UITEST_EXECUTION_MODE=node` |
| P0-4 evidence | 1 | ✅ `status=pass`（本地镜像 + 节点 E2E） |
| 守卫 | P0-4 转绿 | ✅ |

## 3. 非目标

- 不在本批部署生产；生产 digest 由同一 Dockerfile 重建后复核；
- 不修 `start-worker.sh` 缺失（既有缺口，单独确认）。

## 4. DoD

- [x] Dockerfile 修复 + 镜像构建 + 无 Chromium 验证；
- [x] P0-4 evidence + 文档；
- [ ] PR merge。
