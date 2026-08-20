---
title: "test-platform-v2 — 测试平台 v2 前后端分离"
owner: "qa-team"
last_reviewed: "2026-08-01"
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
├── frontend/         React 19.2.8 + React Router 8.3.0 + shadcn/ui + Vite 7.3.6
├── deploy/           docker-compose 一键部署 (Nginx 反代)
└── docs/             PRD + 架构图 + 接入指南 + Backlog
```

- **角色**：一体化测试管理平台，覆盖「需求 → AI 用例 → 用例库 → 测试计划 → 执行 → 报告/缺陷」主链路
- **通信**：前后端仅通过 REST API 通信，前端 Nginx 反代 `/api` 到后端
- **认证**：BCrypt + JWT；浏览器以 `httpOnly` Cookie 为主会话，登录响应和内存 Token 仅保留 Bearer 过渡兼容；RBAC 使用权限点和 global/project/self 数据范围

## 功能模块成熟度

> `✅` 仅表示本地受控链路已有可复核证据；`🟡` 表示真实实现但生产级矩阵不完整；`⛔` 表示缺外部条件或明确延期。Batch 60 总体判定为 `NEEDS WORK`，production 发布为 `DEFERRED`，不得把单模块实现直接写成“生产可用”。

| 模块 | 路由 | 成熟度 | 说明 |
|------|------|--------|------|
| 登录鉴权 / 项目切换 | `/login` | 🟡 | Cookie 主会话 + Bearer 兼容回退；全模块项目切换、会话失效和强制改密门禁仍待矩阵验收 |
| 用户/角色/权限 RBAC | `/system` | 🟡 | 三级数据范围与审计存在；admin/tester/viewer 全能力矩阵未完成 |
| 项目管理 | `/project` | ✅ | 多项目、成员、主题与停用语义已有本地证据 |
| 工作台 / 用例 / 计划 / 报告 | `/workbench` `/testcase` `/testplan` `/report` | 🟡 | 核心本地闭环真实可用；跨页查询、批量破坏操作、全路由权限和可访问性仍需回归 |
| 缺陷 / 定时 / 追溯 | `/defect` `/schedule` `/trace` | 🟡 | 状态流、定时和追溯链存在；全量 UI/API/DB/审计一致性与三身份矩阵未完成 |
| 需求 | `/requirement` | 🟡 | 本地持久化与展示可用；真实 LLM、蓝湖与旧 PostgreSQL 快照验收受外部输入阻塞 |
| 用例脑图 | `/testcase?tab=mindmap` | 🟡 | P2a 起并入用例服务「脑图视图」Tab（`/mindmap` 重定向，菜单种子移除）；脑图内容实际为用例 taxonomy 聚合 |
| API 测试 | `/apitest` | 🟡 | OpenAPI/Swagger 导入、httpx 执行、任务/快照已实现；五入口一致性、生产保护与 Test5 当前契约待验收 |
| UI 自动化 | `/uitest` | 🟡 | 本地 Runner、环境注入和产物闭环已验证；不能替代体育 Test5/生产业务 E2E |
| ~~音视频专项~~ | ~~`/special`~~ | 已移除 | batch-165 隐藏菜单后，代码已随死代码清理批次整体删除（路由/服务/模型/页面）；如需恢复从 git 历史取回 |
| 环境 / 数据集 | `/environment` `/dataset` | 🟡 | 项目级数据和变量链可用；生产目标防误触发仍需统一验证 |
| 通知 / 集成 | `/notify` `/integration` | ⛔（默认隐藏） | 本地模型和错误路径存在；真实 SMTP/Webhook/Jira/TAPD/ELK 缺非生产凭据与端点。P1a 起入口默认经 `DISABLED_MENUS` 软下线（侧边栏+访客目录+命令面板隐藏，页面路由保留可直达），恢复：`DISABLED_MENUS=` 置空 |
| 知识 / 发布包 | `/knowledge` `/release-bundles` | 🟡 | 无 AI/Wiki/活动发布包时已 fail closed；外部链路和交互标注回归未全部完成。~~Agent 工作台~~：P1b 起入口收敛进 DSH 任务（页面删除，`/agent-workbench` 重定向 `/dsh-tasks`；`/api/v1/agent` 后端 API 保留供知识/排障链路与调试调用） |
| AI 配置 / DSH 任务 | `/ai-config` `/dsh-tasks` | 🟡 | 项目级 AI 提供方池（Batch A）+ DSH 执行入口（Batch 172/191/202）；无配置即禁用 AI，未配置引导入口已接入 |
| 开放 API | API-only `/api/v1/open` | 🟡 | 独立 API Token Bearer 鉴权；属于 API-only 能力，前端入口和生产级契约验收不完整 |
| ~~性能监控~~ | ~~`/perftest`~~ | 已移除 | 缺 SoloX/真机等外部条件从未可用；代码已随死代码清理批次整体删除（含 WebSocket 采集）；如需恢复从 git 历史取回 |
| 主题实验室 | `/theme-lab` | ✅ | 本地设计/响应式验证工具，不是业务生产能力 |
| 运维发布控制 | 独立项目，无产品路由 | ⛔ | Batch 61 在 `../deploy/release-control/` 建设 test-only CLI/领域库；生产适配拒绝，控制面 API/UI 延后到 Batch 62 |

## 契约与测试证据边界

- FastAPI 版本以 `backend/requirements.lock` 的 `0.140.13` 为可复现基线；`requirements.txt` 的 `>=0.110` 只是声明下限。前端锁文件基线为 React `19.2.8`、React Router `8.3.0`、Vite `7.3.6`。
- FastAPI 在 `/openapi.json` 生成运行时契约，文档入口为 `/docs` 与 `/redoc`；业务 API 前缀为 `/api/v1`，`/health` 独立。`npm run gen:api` 需要显式刷新前端生成类型，生成文件不能代替运行时契约检查。
- API 资产导入支持 OpenAPI 3.x / Swagger 2.0 的 JSON/YAML 文本或 URL，以及 Knife4j/Swagger 文档来源的预览/确认；导入成功不等于目标环境接口回归通过。
- `backend/tests/playwright/specs/` 验证测试平台本地 Runner；`../tests/automation/ui/` 才是体育用户端/运营后台业务 E2E。两类结果必须分开统计和索引。

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
