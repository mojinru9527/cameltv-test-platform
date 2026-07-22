---
title: "CamelTv 测试自动化平台 — AI 编码助手入口"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["project-overview", "ai-entry", "architecture"]
related: ["test-platform-v2/CLAUDE.md", "docs/adr/README.md", "COMMANDS.md"]
---

# CamelTv 测试自动化平台

> AI 编码助手入口文件。本文件为仓库级 system prompt，为 AI 提供项目全景、架构原则和导航索引。

## 项目定位

为 **CamelTv 体育平台**（用户端 + 运营后台）提供全链路测试能力的一体化测试平台。覆盖：
- **管理闭环**：需求 → AI 生成用例 → 用例库 → 测试计划 → 执行 → 报告/缺陷
- **专项测试**：API 测试、UI 自动化、音视频质量检测
- **CI/CD 集成**：Jenkins Pipeline + GitHub Actions 双通道

## 仓库地图

| 路径 | 模块 | 技术栈 | 状态 | 说明 |
|------|------|--------|------|------|
| [test-platform-v2/](test-platform-v2/CLAUDE.md) | 测试平台 v2 主力 | FastAPI + React 18 | **活跃开发** | 前后端分离，RBAC，AI 驱动 |
| [test-platform/](test-platform/CLAUDE.md) | 测试平台 v1 旧版 | FastAPI + React 18 | 维护模式 | 单体架构，CLI 工具套件 |
| [lanhu-mcp/](lanhu-mcp/CLAUDE.md) | 蓝湖 MCP 服务 | FastMCP + Playwright | 稳定 | 桥接蓝湖原型与 AI 编码助手 |
| [tests/](tests/CLAUDE.md) | 测试资产 | Markdown + Playwright | 持续积累 | 功能用例 + API 测试 + 自动化 |
| [deploy/](deploy/CLAUDE.md) | CI/CD 部署 | Jenkins + Docker + GitHub Actions | 稳定 | 11 阶段 Pipeline |

## 架构原则

1. **前后端物理隔离**：v2 的 `backend/` 和 `frontend/` 独立部署、独立 CI/CD，仅通过 REST API 通信
2. **SQLite 优先，可升级 PostgreSQL**：开发/测试环境用 SQLite WAL，通过 Alembic 迁移支持升级
3. **纯 Python 单栈**：后端全栈采用 Python FastAPI，放弃 Java/PHP 多栈方案
4. **测试金字塔**：P0（核心必测）→ P3（次要），自动化优先覆盖 P0/P1
5. **AI 原生**：DeepSeek LLM 驱动用例生成，蓝湖 MCP 驱动需求分析

## 关键约定

- **版本号**：引用蓝湖「更新日志」页产品手写版本号（用户端 14.1.0 / 运营后台 8.2.0），非系统版本号
- **用例规范**：所有功能用例和接口用例必须遵循 [tests/test-case-standards/](tests/test-case-standards/) 下的标准
- **命名规范**：测试用例 `TC-{模块}-{编号}.md`，需求文档 `{系统}-{版本}-需求规格说明书.md`
- **Git 规范**：功能分支 `feature/xxx`，修复分支 `fix/xxx`，主分支 `develop`（PR 合并，禁止直接 push）
- **任务完成**：每次任务完成后需明确回复"该任务已完成"

## 环境速览

| 环境 | 用途 | 部署方式 |
|------|------|---------|
| localhost | 本地开发 | `uvicorn` + `npm run dev` |
| test | 测试环境 | Jenkins 自动部署 |
| staging | 预发布 | 手动 docker compose |
| prod | 生产环境 | 需 VPN 接入 |

## 常用命令入口

- 命令速查：[COMMANDS.md](COMMANDS.md)
- v1 CLI: `tp --help`
- v2 后端: `uvicorn app.main:app --reload --port 8000`
- v2 前端: `npm run dev`（端口 5173）
- 蓝湖 MCP: `python lanhu_mcp_server.py`（端口 8000）
- Jenkins 本地: `cd deploy/jenkins && docker compose up -d`（端口 8080）

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 建设方案 | [CamelTv-测试自动化平台-建设方案.md](CamelTv-测试自动化平台-建设方案.md) | 顶层架构方案 |
| 重构方案 | [测试平台-前后端分离重构方案.md](测试平台-前后端分离重构方案.md) | v1→v2 重构设计 |
| v2 PRD | [test-platform-v2/docs/CamelTv测试平台-完整PRD.md](test-platform-v2/docs/CamelTv测试平台-完整PRD.md) | v2 完整产品需求 |
| v2 接入指南 | [test-platform-v2/docs/onboarding.md](test-platform-v2/docs/onboarding.md) | 新项目接入流程 |
| v2 改进 Backlog | [test-platform-v2/docs/改进任务backlog.md](test-platform-v2/docs/改进任务backlog.md) | 待领任务清单 |
| ADR | [docs/adr/](docs/adr/) | 架构决策记录 |
| 命令速查 | [COMMANDS.md](COMMANDS.md) | 所有服务的命令速查 |

## AI 协作指引

- 本文件为 AI 第一入口。各子项目 CLAUDE.md 包含模块级约定和细节。Agent 工作流规范见 [AGENTS.md](AGENTS.md)
- Memory 系统位于 `~/.claude/projects/f--CamelTv/memory/`，存储跨会话的偏好和约定
- 蓝湖原型内容通过 lanhu-mcp 工具获取，不要在 CLAUDE.md 中硬编码原型内容
- 做架构级决策时，先查阅 [docs/adr/](docs/adr/)，并在 PR 中考虑是否需新增 ADR
