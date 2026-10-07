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

> v2.1 重构版本。按《测试平台-前后端分离重构方案 v2.1》搭建；重构前的 v1（`test-platform/`）已于 Batch 100 整体退役移除，不再有需要物理隔离的并存目录。

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

> `✅` 仅表示本地受控链路已有可复核证据；`🟡` 表示真实实现但生产级矩阵不完整；`⛔` 表示缺外部条件或明确延期。
> **平台简化批次（2026-10-07）**：AITDE（智能测试任务/场景/契约/Durable Runtime/愈合/Flaky/生产证据）、DSH 任务、报告中心、测试数据集、通知、集成、组织管理、主题实验室、知识图谱/AI 审核台/平台研发等已**整体删除**（代码 + 库表 + 迁移），详见 `docs/platform-refactor/11-platform-simplification-design.md` 与 `work-logs/platform-simplification-production-eval-20261007.md`。

| 模块 | 路由 | 成熟度 | 说明 |
|------|------|--------|------|
| 登录鉴权 / 项目切换 | `/login` | 🟡 | Cookie 主会话 + Bearer 兼容回退；全模块项目切换、会话失效和强制改密门禁仍待矩阵验收 |
| 用户/角色/权限 RBAC | `/system` | 🟡 | 三级数据范围与审计存在；admin/tester/viewer 全能力矩阵未完成 |
| 项目管理 | `/my-projects` | ✅ | 多项目、成员、主题与停用语义；组织概念已删除（项目成员直管） |
| 工作台 / 用例 | `/workbench` `/testcase` | 🟡 | 核心本地闭环真实可用；跨页查询、批量破坏操作、全路由权限和可访问性仍需回归 |
| 测试计划（只读归档） | `/test-plans`（仅 GET） | 🟡 | 前端入口已删（batch-212）；后端只读 API + 历史表保留（工作台/缺陷统计底座），写入口已删除 |
| 缺陷 / 定时 | `/defect` `/schedule` | 🟡 | 状态流和定时存在；全量 UI/API/DB/审计一致性与三身份矩阵未完成 |
| 需求 | `/requirement` | 🟡 | 本地持久化 + AI 生成用例（平台直连 LLM）+ 蓝湖证据面板 |
| 用例脑图 | `/testcase?tab=mindmap` | 🟡 | P2a 起并入用例服务「脑图视图」Tab；脑图内容为用例 taxonomy 聚合 |
| API 测试 | `/apitest` | 🟡 | OpenAPI/Swagger 导入、httpx 执行、任务/快照已实现；智能生成用例/泛化保留 |
| UI 自动化 | `/uitest` | 🟡 | 本地 Runner、环境注入和产物闭环已验证；不能替代体育 Test5/生产业务 E2E |
| 环境 | `/environment` | 🟡 | 项目级数据和变量链可用；生产目标防误触发仍需统一验证 |
| 版本发布包 / 版本验收任务 | `/release-bundles` `/version-tasks` | 🟡 | 版本唯一事实源（Batch 216/269/270 试点证据）；执行走 ExecutionJob 协议 + cameltv-node 本地节点 |
| 知识中心（项目知识库） | `/knowledge` | 🟡 | 影响面/项目知识/检索 + 维护面（概览/知识源/版本记录/复用建议/Wiki）；知识图谱/AI 审核台已删除 |
| AI 配置 | `/ai-config` | 🟡 | 项目级 AI 提供方池（Batch A）；需求 AI 生成与版本任务 AI 方案经此解析 |
| 蓝湖证据包 | `/lanhu-evidence` | 🟡 | 采集/OCR/人工审核 |
| 开放 API | API-only `/api/v1/open` | 🟡 | 独立 API Token Bearer 鉴权；CI 回归回写入口 |
| ~~AITDE / DSH / 报告 / 数据集 / 通知 / 集成 / 组织 / 主题实验室 / 性能监控 / 音视频专项~~ | 已删除 | 已移除 | 平台简化批次整体删除（见顶部说明）；如需恢复从 git 历史取回 |

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
- [clean-code-standards.md](clean-code-standards.md) — 适配本平台的 Clean Code 代码规范（命名/函数/错误/分层/测试/AI 生成）
- [代码开发校验门禁（减少返工）](../../docs/code-development-gate.md) — G0–G4 五道门禁，整合 Clean Code + Gherkin 验收 + QA 管理；本地一键 `scripts/git/dev-gate.ps1`

## 凭据策略

部署账号密码通过未跟踪的 `.env` 或 Secret 管理注入，登录页不预填凭据。仓库、文档、测试报告和截图禁止保存真实密码、Token、API Key、Webhook 或 VPN 文件。

## 关联文档

- 完整 PRD：[docs/CamelTv测试平台-完整PRD.md](docs/CamelTv测试平台-完整PRD.md)
- 现状功能：[docs/现状功能PRD.md](docs/现状功能PRD.md)
- 代码审查/重构：[docs/代码审查与产品重构PRD.md](docs/代码审查与产品重构PRD.md)
- 改进 Backlog：[docs/改进任务backlog.md](docs/改进任务backlog.md)
- 接入指南：[docs/onboarding.md](docs/onboarding.md)
- 架构图：[docs/diagrams/](docs/diagrams/)（18 张 Mermaid + PNG）
