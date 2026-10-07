---
title: "CamelTv 测试自动化平台 — 仓库说明"
owner: "qa-team"
last_reviewed: "2026-09-24"
status: "active"
expires: "2027-03-24"
tags: ["readme", "project-overview", "quickstart", "commands"]
related: ["CLAUDE.md", "AGENTS.md", "COMMANDS.md", "docs/adr/README.md"]
---

# CamelTv 测试自动化平台

> 为 **CamelTv 体育平台**（用户端 + 运营后台）提供全链路测试能力的一体化测试平台。
> 本文档面向所有进入仓库的人：项目是什么、代码在哪、怎么跑起来、去哪里查。
> AI 编码助手请先读 [CLAUDE.md](CLAUDE.md)（仓库级 system prompt）；Agent 分支/提交/PR 流程见 [AGENTS.md](AGENTS.md)。

覆盖三条主线：

- **管理闭环**：需求 → AI 生成用例 → 用例库 → 测试计划 → 执行 → 报告/缺陷
- **专项测试**：API 测试、UI 自动化、音视频质量检测
- **CI/CD 集成**：Jenkins Pipeline + GitHub Actions 双通道

## 仓库地图

| 路径 | 模块 | 技术栈 | 状态 | 说明 |
|------|------|--------|------|------|
| [test-platform-v2/](test-platform-v2/README.md) | 测试平台 v2 主力 | FastAPI + React | **活跃开发** | 前后端分离，RBAC，需求 AI 生成用例 |
| ~~test-platform/~~ | 测试平台 v1 旧版 | FastAPI + React | ✅ 已退役（Batch 100） | 整体移除；API 回归资产迁移至 [tests/api-testing/](tests/api-testing/README.md) |
| [lanhu-mcp/](lanhu-mcp/) | 蓝湖 MCP 服务 | FastMCP + Playwright | 稳定 | 桥接蓝湖原型与 AI 编码助手 |
| ~~knowledge-mcp/~~ | 知识中心 MCP 服务 | FastMCP + httpx | ✅ 已删除（平台简化批次） | 随 DSH 测试 Agent 一并移除 |
| [tests/](tests/README.md) | 测试资产 | Markdown + Playwright | 持续积累 | 功能用例 + API 测试 + 自动化 |
| [deploy/](deploy/CLAUDE.md) | CI/CD 部署 | Jenkins + Docker + GitHub Actions | 稳定 | 11 阶段 Pipeline |

根级关键文件：[CLAUDE.md](CLAUDE.md)（AI 第一入口）、[AGENTS.md](AGENTS.md)（Agent 工作流规范）、[COMMANDS.md](COMMANDS.md)（命令速查）、[C-CONDITIONS.md](C-CONDITIONS.md)（验收条件事实源）、[Jenkinsfile](Jenkinsfile)、[repo-boundaries.json](repo-boundaries.json)。

## 快速开始

平台只采用两套独立实例，**浏览器地址即环境**，页面内不切换数据库（见 [test-platform-v2/README.md](test-platform-v2/README.md)）：

| 环境 | 固定入口 | 数据库 |
|------|----------|--------|
| local | `http://localhost:5173` | 独立 SQLite `platform-local.db` |
| production | `https://swiftbugs.cn` | 生产 PostgreSQL（腾讯云广州单机 Docker Compose） |

### 全栈一键启动（推荐）

```powershell
# 首次运行：安全生成受 Git 忽略的 local.env 和固定本地凭据
pwsh test-platform-v2/scripts/start-platform-environment.ps1 `
  -Target local -Action start -InitializeLocal

# 后续运行
pwsh test-platform-v2/scripts/start-platform-environment.ps1 -Target local -Action start
```

### 后端（FastAPI）

```bash
cd test-platform-v2/backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.lock
uvicorn app.main:app --reload --port 8000
```

### 前端（React，另开终端）

```bash
cd test-platform-v2/frontend
npm ci
npm run dev
```

浏览器打开 `http://localhost:5173`，使用管理员分配的账号登录。**平台不预填或公开通用默认密码**；普通用户由管理员在「系统管理」中创建。
后端 API 文档：`/docs`（Swagger UI）、`/redoc`、`/openapi.json`；健康检查 `/health`，业务路由统一在 `/api/v1`。

## 常用命令

> 完整命令速查见 [COMMANDS.md](COMMANDS.md)。下表只列日常必用项，均取自 COMMANDS.md 与 [test-platform-v2/README.md](test-platform-v2/README.md)。

| 场景 | 命令 |
|------|------|
| 后端：全量测试 | `cd test-platform-v2/backend && python -m pytest tests/ -v --tb=short` |
| 后端：单文件测试 | `python -m pytest tests/test_auth.py -v` |
| 后端：Lint 硬门禁 | `ruff check app/ --select F821` |
| 前端：类型检查 | `cd test-platform-v2/frontend && npm run typecheck` |
| 前端：构建 | `npm run build` |
| 前端：单元测试 | `npm test` |
| 前端：可访问性（CI 口径） | `npm run test:a11y:ci` |
| 前端：刷新 API 类型 | `npm run gen:api`（需后端 `/openapi.json` 可访问） |
| API 回归：环境探活 | `pwsh scripts/ci/api-regression.ps1 health -BaseUrls "https://camelive-g3-test5.elelive.cn/,https://g3-test3.elelive.cn/"` |
| API 回归：全量运行 | `pwsh scripts/ci/api-regression.ps1 run -BaseUrl "https://g3-test3.elelive.cn" -AuthToken $env:CAMELTV_AUTH_TOKEN -ReportDir "artifacts"` |
| 本地执行节点：首次签发令牌 | `python scripts/node/cameltv_node/cli.py login --username <平台账号> --project-id <项目ID>` |
| 本地执行节点：开工 | `python scripts/node/cameltv_node/cli.py up --node-id my-pc --capabilities api web` |
| 蓝湖 MCP 服务 | `cd lanhu-mcp && python lanhu_mcp_server.py`（端口 8000；`lanhu-mcp` 是 Git 子模块，需先 `git submodule update --init`） |
| Jenkins 本地 | `cd deploy/jenkins && docker compose up -d`（端口 8080） |
| 一键开发门禁（G0–G2） | `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path`（在仓库根执行，串起提交卫生 + ruff F821 + 前端 typecheck/lint + 路由守卫测试） |

## 环境

| 环境 | 用途 | 部署方式 |
|------|------|---------|
| localhost | 本地开发 | `uvicorn` + `npm run dev` |
| test | 测试环境 | 本地/测试实例 Docker Compose（staging 替代） |
| staging | 预发布 | **未单独启用**（以 test/生产同构实例 + 本地全栈承担，见 [docs/agent-team/staging-environment.md](docs/agent-team/staging-environment.md)） |
| prod | 生产环境 | 腾讯云广州单机 `https://swiftbugs.cn`（Caddy→Nginx→FastAPI→PostgreSQL；旧 Vercel/Railway/Supabase 已于 2026-08-22 下线，迁移见 [docs/ops/tencent-cloud-migration.md](docs/ops/tencent-cloud-migration.md)） |

## 进一步阅读

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | AI 编码助手第一入口：项目全景、架构原则、导航索引 |
| [AGENTS.md](AGENTS.md) | Agent 工作流规范：分支命名、Git 门禁、提交前自检、发布节奏 |
| [COMMANDS.md](COMMANDS.md) | 所有服务的命令速查（含本地执行节点、知识与验收脚本） |
| [docs/adr/](docs/adr/) | 架构决策记录（ADR 索引与状态） |
| [docs/repo-map.md](docs/repo-map.md) | 仓库完整导航地图 |
| [docs/engineering-standards.md](docs/engineering-standards.md) | 工程规范（含 React 副作用与 API 请求规范） |
| [docs/testing-strategy.md](docs/testing-strategy.md) | 测试策略总纲：分层、工具选型、执行频率 |
| [docs/common-pitfalls.md](docs/common-pitfalls.md) | 常见陷阱与已知问题排查 |
| [docs/agent-team/release-cadence.md](docs/agent-team/release-cadence.md) | 版本发布节奏：合代码 ≠ 发版本 |
| [docs/ops/restore-drill.md](docs/ops/restore-drill.md) | 生产备份恢复演练手册 |
| [test-platform-v2/docs/onboarding.md](test-platform-v2/docs/onboarding.md) | 新项目接入流程 |

## 关键约定（摘要）

- **单一主干**：唯一主干 `main`；功能分支 `feature/xxx`、修复分支 `fix/xxx`、热修复 `hotfix/xxx`、发布 `release/xxx`。禁止直接 push 主干，必须独立 worktree + PR + required checks。详见 [AGENTS.md](AGENTS.md)。
- **文档保鲜**：`CLAUDE.md`、`README.md`、`docs/` 与 `tests/README.md` 遵循 [docs/document-standards.md](docs/document-standards.md)（YAML frontmatter + 审核周期）。
- **凭据**：真实密码、Token、API Key、Webhook、VPN 文件与 `.env` 一律不得提交到 Git。
- **任务完成**：每次任务完成后需明确回复"该任务已完成"。
