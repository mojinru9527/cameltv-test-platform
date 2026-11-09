# Batch 277b-6 — QA Report

> **部门**：🔍 QA · **日期**：2026-11-09

## 1. 生产验收

| 项 | 结果 | 证据 |
|----|:----:|------|
| 部署前备份 | ✅ | `pre-deploy-20261109-233841.dump`（168MB，sha256 `edff0f09…`） |
| 迁移 | ✅ | head `20261110_b277b_ui_run_exec_job`；public 表 94 |
| 首次迁移失败处置 | ✅ | `report_template` FK → 回滚 prev 镜像（health 200）→ 修 CASCADE → 重试成功 |
| 健康 | ✅ | `/api/v1/open/health` 200、`/login` 200、public-access 200 |
| 镜像 | ✅ | `sha256:23c02e8894f7…`，812MB，无 chromium，`/ms-playwright` 空 |
| `/uitest` | ✅ | 生产 run 481（job 3255），1/1 pass，3 文件，4.05s |
| Key | ✅ | 3 provider 更新；`ai_client.chat_completions` → OK |
| ai-gateway | ✅ | 容器已停止并删除 |
| 磁盘 | ✅ | 清理上传包后 77% |
| 守卫 | ✅ | `GATE_RESULT=PASS` 5/5 |

## 2. 风险 / 已知

| 项 | 说明 |
|----|------|
| 旧 compose 与 repo 不同步 | 服务端 compose 仍含 ai-gateway 定义（容器已删，`--no-deps` 部署不会重建）；后续批次同步 |
| 单 Key 复用 | 3 条 provider 同一把；建议后续拆 4 把 |
| 浏览器功能降级 | 蓝湖截图 / XHR / Playground 当前 503/error，需迁移批次 |
| 回滚镜像 | `cameltv-tp-backend:prev-20261109` 保留 |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 1h / 实际 ≈ 1h20m（含一次回滚） |
| 缺陷 | 2（DROP 顺序 FK、compose 未注入 AI_API_KEY） |
| 返工 | 2 次部署 |
| 根因 | 迁移从未在 PostgreSQL 实跑；生产 compose 是旧版本 |
| 下次避免 | 生产同构库先跑迁移；部署前 diff server compose 与 repo |
