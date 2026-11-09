# Batch 277b-6 — 生产部署（P0 清零）：PRD-lite

> **部门**：🟦 Product（lite） · **日期**：2026-11-09 · **批次模式**：light（运维发布 + 证据）
> **分支**：fix/batch-277b-6-prod-deploy（基线 `1109d0b74`）

## 1. 目标

用户授权：提供新 Key、P0-3 豁免 48h、立即发布生产。完成 P0-1..5 生产闭环。

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| 生产迁移到 head | 1 | ✅ `20261110_b277b_ui_run_exec_job` |
| 104 表 DROP 完成 | 1 | ✅ public 表 94 |
| 服务健康 | 200 | ✅ health/login/public-access |
| 无 Chromium 镜像上线 | 1 | ✅ sha256:23c02e88… |
| 生产 `/uitest` 节点执行 | 1 | ✅ run 481，1/1 pass |
| Key 轮换 + 真实调用 | 1 | ✅ 3 provider + `ai_client` OK |
| ai-gateway 退役 | 0 容器 | ✅ 已 stop/rm |
| 守卫 | 5/5 | ✅ PASS |

## 3. 非目标

- 不迁移蓝湖截图 / XHR / Playground（当前显式降级，后续批次）；
- 不拆 4 把独立 Key（本次 1 把复用 3 provider）。

## 4. DoD

- [x] 备份 → 迁移 → 回滚预案 → 重试 → 健康；
- [x] P0 证据 5 份 + 守卫 PASS；
- [x] PR 合入。
