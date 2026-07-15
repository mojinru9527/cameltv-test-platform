---
title: "test-platform-v2 — 测试平台 v2 前后端分离"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["test-platform", "v2", "fastapi", "react"]
related: ["backend/CLAUDE.md", "frontend/CLAUDE.md", "docs/CamelTv测试平台-完整PRD.md", "../docs/adr/0003-frontend-backend-physical-separation.md"]
---

# test-platform-v2 — 测试平台 v2（前后端分离）

> v2.1 重构版本，与 `../test-platform/`（旧版）物理隔离。按《测试平台-前后端分离重构方案 v2.1》搭建。

## 架构概览

```
test-platform-v2/
├── backend/          FastAPI + SQLAlchemy 2.0 + SQLite (WAL)
├── frontend/         React 18 + shadcn/ui (Radix + Tailwind) + Vite 5
├── deploy/           docker-compose 一键部署 (Nginx 反代)
└── docs/             PRD + 架构图 + 接入指南 + Backlog
```

- **角色**：一体化测试管理平台，覆盖「需求 → AI 用例 → 用例库 → 测试计划 → 执行 → 报告/缺陷」主链路
- **通信**：前后端仅通过 REST API 通信，前端 Nginx 反代 `/api` 到后端
- **认证**：JWT + BCrypt，完整 RBAC（权限点 + 三级数据范围：global/project/self）

## 功能模块成熟度

| 模块 | 路由 | 成熟度 | 说明 |
|------|------|--------|------|
| 登录鉴权 / 项目切换 | `/login` | ✅ 生产可用 | bcrypt + JWT，多项目隔离 |
| 用户/角色/权限 RBAC | `/system` | ✅ 生产可用 | 三级数据范围 + 审计日志 |
| 用例服务 CRUD + 域树 | `/testcase` | ✅ 生产可用 | 批量操作、域/模块树、Excel/Xmind 导出入、版本历史 |
| 测试计划 + 执行闭环 | `/testplan` | ✅ 生产可用 | pass/fail/skip/block，ELK traceId |
| 工作台看板 | `/workbench` | ✅ 生产可用 | Recharts 图表 |
| 报告中心 | `/report` | ✅ 生产可用 | JSON 快照，CSV/Excel 导出 |
| 定时任务 | `/schedule` | ✅ 生产可用 | APScheduler + Cron 表达式 |
| 需求管理 + AI 生成 | `/requirement` | ✅ 生产可用 | DeepSeek LLM 两段式生成+反向评审 |
| 质量追溯矩阵 | `/trace` | ✅ 生产可用 | 项目覆盖率 + 单用例全链路追溯 |
| 缺陷管理 | `/defect` | ✅ 生产可用 | 6 状态状态机 + 评论 + 附件 |
| 开放 API | `/open` | ✅ 生产可用 | Token 鉴权 + 触发 + 查询 + 结果回写 |
| 通知中心 | `/notify` | ✅ 生产可用 | Webhook + 邮件，4 事件触发，重试/日志 |
| 环境/变量管理 | `/environment` | ✅ 生产可用 | 项目级 dev/test/staging/prod，AES-128 加密变量 |
| 项目管理 | `/project` | ✅ 生产可用 | 多项目 + 成员 + 主题 |
| API 测试 | `/apitest` | 🟡 真实执行，能力待生产化 | httpx 真实 HTTP 请求，缺请求快照/任务取消/生产保护 |
| UI 自动化 | `/uitest` | 🟡 真实执行，能力待生产化 | npx playwright test 真实执行，缺异步/环境注入/产物归档 |
| 音视频专项 | `/special` | 🧪 演示态 | 指标为 random 模拟 |

## 关键架构决策

- **为何纯 Python**：统一技术栈，降低维护复杂度 → 参见 [ADR-0001](../docs/adr/0001-use-python-fastapi-monostack.md)
- **为何 SQLite**：开发零配置，WAL 模式支持并发读，Alembic 支持升级 PostgreSQL → 参见 [ADR-0002](../docs/adr/0002-sqlite-with-postgresql-upgrade-path.md)
- **为何 shadcn/ui**：Radix 无障碍 + Tailwind 原子化 + 组件源码可控 → 参见 [ADR-0006](../docs/adr/0006-shadcn-ui-over-antd.md)

## 子模块索引

- [backend/CLAUDE.md](backend/CLAUDE.md) — 后端架构、API 约定、服务层模式
- [frontend/CLAUDE.md](frontend/CLAUDE.md) — 前端架构、组件库、状态管理约定

## 凭据策略

部署账号密码通过未跟踪的 `.env` 或 Secret 管理注入，登录页不预填凭据。仓库、文档、测试报告和截图禁止保存真实密码、Token、API Key、Webhook 或 VPN 文件。

## 关联文档

- 完整 PRD：[docs/CamelTv测试平台-完整PRD.md](docs/CamelTv测试平台-完整PRD.md)
- 现状功能：[docs/现状功能PRD.md](docs/现状功能PRD.md)
- 代码审查/重构：[docs/代码审查与产品重构PRD.md](docs/代码审查与产品重构PRD.md)
- 改进 Backlog：[docs/改进任务backlog.md](docs/改进任务backlog.md)
- 接入指南：[docs/onboarding.md](docs/onboarding.md)
- 架构图：[docs/diagrams/](docs/diagrams/)（18 张 Mermaid + PNG）
