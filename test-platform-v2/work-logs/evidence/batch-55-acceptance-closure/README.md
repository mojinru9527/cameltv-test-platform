---
title: "Batch 55 验收收尾证据索引"
owner: "qa-team"
last_reviewed: "2026-07-29"
status: "active"
tags: ["batch-55", "evidence", "redacted"]
---

# Batch 55 验收收尾证据索引

## 证据规则

- 状态仅使用 `PASS`、`FAIL`、`BLOCKED`、`NOT RUN`。
- 每条记录必须包含用例 ID、提交 SHA、命令、退出码、时间、环境和脱敏结果。
- 截图、Trace 和浏览器报告只记录可复现路径；生成目录保持 ignored，不提交大体积产物。
- 不记录密码、Token、Cookie、Authorization 头、个人信息或真实生产业务数据。
- 临时 SQLite 迁移演练不能替代 A10 的真实旧 PostgreSQL 快照升级证据。

## 环境

| 项 | 值 |
|---|---|
| 基线 | `origin/main@ad62aaecc1cc26ee8a54a8211a9b6336a5942eb3` |
| 分支 | `fix/batch-55-acceptance-closure` |
| 工作流 / 执行器 | `agent-team` / `codex` |
| 本地前端 | `http://localhost:5193` |
| 本地后端 | `http://127.0.0.1:8023` |
| 数据库 | 工作树隔离的 SQLite |

## 证据记录

| 用例 ID | 状态 | 提交 SHA | 命令 | 退出码 | 时间 | 环境 / 证据 | 脱敏 |
|---|---|---|---|---:|---|---|---|
| B55-WT-01 | PASS | `ad62aaecc1cc26ee8a54a8211a9b6336a5942eb3` | `verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex` | 0 | 2026-07-29 14:28 +08:00 | `F:\CamelTv-worktrees\codex-batch-55-acceptance-closure` | PASS |
| B55-SEED-01 | NOT RUN | — | 聚焦 Pytest 与 Ruff | — | — | 本地后端 | — |
| B55-PROXY-01 | NOT RUN | — | Vitest 代理契约 | — | — | 本地前端 | — |
| B55-BROWSER-01 | NOT RUN | — | Playwright `/apitest` 与登录壳验收 | — | — | 5193 → 8023 | — |
| B55-MIGRATION-01 | NOT RUN | — | 临时数据库迁移契约 | — | — | 本地后端 | — |
| B55-A10-LEGACY-DB | BLOCKED | — | 真实旧 PostgreSQL 快照升级 | — | 2026-07-29 | 未提供脱敏旧库快照与 PostgreSQL 验收连接 | PASS |
| B55-EXTERNAL-01 | NOT RUN | — | 外部环境只读验收 | — | — | 明确安排在 Batch 56 | — |
| B55-FULL-GATE | NOT RUN | — | 后端/前端全量门禁 | — | — | 本地工作树 | — |

## ClearType 非缺陷证据

| 证据 | 观察 |
|---|---|
| 实际登录标题计算样式 | 标题及祖先 `text-shadow: none`、`filter: none` |
| CSS-free Segoe UI 控制页 | 同样出现青橙子像素边 |
| Chromium `--disable-lcd-text` 控制页 | 青橙边消失 |

该现象归因于 Windows Chromium 的 ClearType 子像素抗锯齿，不通过文字阴影、滤镜或颜色偏移进行 CSS 修补。

