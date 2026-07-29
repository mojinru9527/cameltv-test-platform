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
| B55-SEED-01 | PASS | `6e4fb6d` | `pytest test_seed_credentials.py test_p1_security_regression.py` | 0 | 2026-07-29 | 44/44；本地临时 SQLite | PASS |
| B55-PROXY-01 | PASS | `df8a4b7` + `b77b53b` | 聚焦 Vitest；typecheck；build | 0 | 2026-07-29 | 13/13；声明输出隔离 | PASS |
| B55-BROWSER-01 | PASS | `7d2aff1` | Playwright `/apitest` 与登录壳验收 | 0 | 2026-07-29 | 1/1；5193 → 8023；四视口 | PASS |
| B55-MIGRATION-01 | PASS | `1f9a06a` | upgrade → explicit downgrade → upgrade → check | 0 | 2026-07-29 | 一次性 SQLite；零漂移 | PASS |
| B55-QUEUE-01 | PASS | `4a6c1db` | Agent queue/permissions/locking Pytest | 0 | 2026-07-29 | 57/57；最终全量确认无尾部噪声 | PASS |
| B55-API-WORKER-01 | PASS | `b48e3ac` | API task worker + seed 聚焦 Pytest | 0 | 2026-07-29 | 20/20；应用退出 join worker | PASS |
| B55-A10-LEGACY-DB | BLOCKED | — | 真实旧 PostgreSQL 快照升级 | — | 2026-07-29 | 未提供脱敏旧库快照与 PostgreSQL 验收连接 | PASS |
| B55-EXTERNAL-01 | NOT RUN | — | 外部环境只读验收 | — | — | 明确安排在 Batch 56 | — |
| B55-FRONTEND-GATE | PASS | `b77b53b` | typecheck + 203 Vitest + build | 0 | 2026-07-29 | 48 files / 203 tests / 3349 modules | PASS |
| B55-BACKEND-GATE | PASS | `b48e3ac` | F821 + 833 Pytest | 0 | 2026-07-29 | 830 passed；3 个既有 PG skip；0 failed；无尾部线程噪声 | PASS |
| B55-SUPPLY-CHAIN | PASS | `4a6c1db` | `npm audit --omit=dev` / `npm audit` | 1 | 2026-07-29 | 通过范围门禁；另有 2 moderate observation、0 high/critical、无依赖变更 | PASS |

## ClearType 非缺陷证据

| 证据 | 观察 |
|---|---|
| 实际登录标题计算样式 | 标题及祖先 `text-shadow: none`、`filter: none` |
| CSS-free Segoe UI 控制页 | 同样出现青橙子像素边 |
| Chromium `--disable-lcd-text` 控制页 | 青橙边消失 |

该现象归因于 Windows Chromium 的 ClearType 子像素抗锯齿，不通过文字阴影、滤镜或颜色偏移进行 CSS 修补。
