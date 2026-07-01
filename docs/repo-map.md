---
title: "CamelTv 仓库地图"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["repo-map", "reference", "navigation", "onboarding"]
related: ["CLAUDE.md", "docs/business-glossary.md", "docs/adr/README.md"]
---

# CamelTv 仓库地图

> 本文档是 CamelTv 仓库的完整导航地图。新人入职第一份文档，也是 AI 编码助手理解项目结构的权威索引。
>
> 仓库地址：`f:\CamelTv` | 主分支：`main`（开发合并至 `master`）

---

## 1. 根级文件

| 文件 | 职责 | 说明 |
|------|------|------|
| `CLAUDE.md` | AI 系统入口 | 仓库级 system prompt，为 AI 提供项目全景、架构原则和导航索引。所有 AI 协作的起点 |
| `COMMANDS.md` | 命令速查手册 | 所有服务的启动、构建、部署命令，按服务/场景分组 |
| `Jenkinsfile` | CI/CD 主流水线 | 11 阶段 Pipeline 定义（Groovy DSL），Jenkins 控制器执行 |
| `.gitignore` | Git 忽略规则 | 排除 venv、node_modules、.env、Docker volumes、测试缓存 |

## 2. 顶级目录一览

### 2.1 `test-platform-v2/` — 主力测试平台（活跃开发）

> **一句话职责**：生产级全链路测试管理平台，覆盖「需求 → AI 用例 → 用例库 → 测试计划 → 执行 → 报告/缺陷」闭环。
>
> **技术栈**：Python 3.12 + FastAPI + SQLAlchemy 2.0 | React 18 + TypeScript + shadcn/ui + Vite 5

| 子目录 | 职责 | 关键文件 |
|--------|------|---------|
| `backend/` | FastAPI 后端服务，提供 REST API、JWT 认证、RBAC 权限、AI 用例生成 | `app/main.py`、`app/core/config.py`、`app/api/v1/router.py` |
| `backend/app/api/v1/` | 17 个 API 路由模块：auth、test_case、test_plan、defect、requirement、report 等 | `auth.py`、`test_case.py`、`test_plan.py` |
| `backend/app/core/` | 核心基础设施：配置、数据库会话、依赖注入、异常处理、安全校验 | `config.py`、`db.py`、`deps.py`、`exceptions.py` |
| `backend/app/services/` | 业务服务层：AI 用例生成、缺陷管理、计划执行、通知推送 | `ai_service.py`、`base_service.py` |
| `backend/app/models/` | SQLAlchemy 2.0 ORM 数据模型 | — |
| `backend/app/schemas/` | Pydantic 请求/响应 schema | — |
| `backend/alembic/` | 数据库迁移脚本（Alembic） | `env.py`、`versions/` |
| `backend/tests/` | pytest 后端单元测试和集成测试 | — |
| `frontend/` | React 18 前端，shadcn/ui + Zustand + React Router 6 | `src/main.tsx`、`src/App.tsx` |
| `frontend/src/components/` | 前端组件库（shadcn/ui 基础组件 + 业务组件） | — |
| `frontend/src/stores/` | Zustand 状态管理（authStore、projectStore 等） | — |
| `frontend/src/api/` | Axios HTTP 客户端，拦截器处理 JWT 刷新和 401 | — |
| `docs/` | v2 专属文档：完整 PRD、接入指南、架构图、改进 Backlog | `CamelTv测试平台-完整PRD.md`、`onboarding.md` |
| `docs/diagrams/` | 18 张 Mermaid + PNG 架构图 | — |
| `deploy/` | v2 Docker Compose 部署编排（Nginx + FastAPI） | `docker-compose.yml` |

### 2.2 `test-platform/` — 测试平台 v1 旧版（维护模式）

> **一句话职责**：旧版单体测试平台，含 10 件 CLI 工具套件，Web 端功能已迁移至 v2。
>
> **技术栈**：Python 3.12 + FastAPI + Click（CLI）| React 18 + Ant Design 5 + Vite

| 子目录 | 职责 | 关键文件 |
|--------|------|---------|
| `cli/` | 统一 CLI 入口 `tp` 命令（Click 框架） | `tp.py` |
| `tools/` | 10 件工具套件：envcheck、api_tester、traffic_monitor、mock_server、api_diff、data_factory、log_aggregator、report_dashboard、project_init、av_checker | 各工具目录下 `__init__.py` |
| `server/` | v1 FastAPI Web 后端（端口 8000） | `main.py` |
| `web-ui/` | v1 React 前端（Ant Design 5，端口 5173） | — |
| `core/` | 核心组件：配置加载器、HTTP 客户端、日志、模型 | `config_loader.py` |
| `config/` | 多站点多环境 YAML 配置系统（_base/site/environment 三级合并） | `environments/test.yaml`、`environments/prod.yaml` |

### 2.3 `lanhu-mcp/` — 蓝湖 MCP 服务器（稳定）

> **一句话职责**：将蓝湖（Lanhu）原型/设计稿暴露为 MCP 工具，供 AI 编码助手调用。
>
> **技术栈**：Python 3.10+ + FastMCP (HTTP) + Playwright Chromium (CDP)

| 子目录 | 职责 | 关键文件 |
|--------|------|---------|
| — | 主服务入口、文档提取、CDP 提取、管理后台提取 | `lanhu_mcp_server.py`、`extract_doc.py`、`extract_cdp.py` |
| — | 一键启动和环境配置脚本 | `quickstart.bat/.sh`、`setup-env.bat/.sh` |
| — | Docker Compose 部署 | `docker-compose.yml`、`Dockerfile` |
| — | Cookie 获取教程 | `GET-COOKIE-TUTORIAL.md` |

### 2.4 `tests/` — 测试资产中心（持续积累）

> **一句话职责**：CamelTv 全链路测试资产：功能用例 + 接口测试 + UI 自动化 + 音视频专项。
>
> **技术栈**：Markdown（用例）| Playwright + TypeScript（UI 自动化）| Python（服务层自动化）

| 子目录 | 职责 | 关键文件 |
|--------|------|---------|
| `test-case-standards/` | 10 篇测试标准规范文档（用例模板、检查清单、优先级定义等） | `测试用例标准.md` |
| `test-cases/functional/` | 功能测试用例：ADMIN / BASELINE / P0-* 分级 | `TC-{模块}-{编号}.md` |
| `test-cases/integration/` | 集成测试用例 | — |
| `test-cases/performance/` | 性能测试用例 | — |
| `test-cases/security/` | 安全测试用例 | — |
| `automation/ui/` | Playwright TypeScript UI 自动化，6 个模块覆盖 | `home/`、`list/`、`detail/`、`pay/`、`refund/`、`bonus/` |
| `automation/service/` | 接口/服务层自动化 | — |
| `automation/fixtures/` | 测试数据与夹具 | — |
| `api-testing/` | 接口测试集合（Postman/Bruno）+ 环境配置 | `collections/`、`environments/` |
| `requirements/` | 需求分析和文档库 | `documents/`、`traceability-matrix/` |
| `音视频测试/` | 10 篇音视频测试指南 | — |
| `音视频项目测试/` | 测试素材 + 分析脚本 | — |

### 2.5 `deploy/` — CI/CD 部署（稳定）

> **一句话职责**：Jenkins Pipeline + GitHub Actions 双通道 CI/CD，Docker Compose 容器化部署。
>
> **技术栈**：Docker + Jenkins + Groovy + GitHub Actions (YAML)

| 子目录 | 职责 | 关键文件 |
|--------|------|---------|
| `jenkins/` | Jenkins Docker 镜像、CasC 自动配置、docker-compose 编排 | `Dockerfile`、`docker-compose.yml`、`casc.yaml` |

### 2.6 `docs/` — 仓库级文档

> **一句话职责**：跨模块的架构文档、决策记录、术语表和标准。

| 子目录/文件 | 职责 |
|-------------|------|
| `docs/document-standards.md` | 所有 Markdown 文档的元数据和编写规范 |
| `docs/business-glossary.md` | 业务术语表，项目内统一语言 |
| `docs/repo-map.md` | 本文档，仓库完整导航地图 |
| `docs/common-pitfalls.md` | 常见陷阱与已知问题库 |
| `docs/adr/` | 架构决策记录（6 篇已采纳 ADR） |
| `docs/adr/0001-use-python-fastapi-monostack.md` | ADR-0001: 采用纯 Python FastAPI 单栈 |
| `docs/adr/0002-sqlite-with-postgresql-upgrade-path.md` | ADR-0002: SQLite 优先，可升级 PostgreSQL |
| `docs/adr/0003-frontend-backend-physical-separation.md` | ADR-0003: 前后端物理隔离 |
| `docs/adr/0004-jwt-bcrypt-rbac-auth.md` | ADR-0004: JWT + BCrypt + RBAC 认证授权 |
| `docs/adr/0005-zustand-over-redux.md` | ADR-0005: 选用 Zustand 而非 Redux |
| `docs/adr/0006-shadcn-ui-over-antd.md` | ADR-0006: 选用 shadcn/ui 而非 Ant Design |

### 2.7 `.github/` — GitHub Actions 工作流

| 文件 | 职责 |
|------|------|
| `workflows/api-regression.yml` | 每日 02:03 UTC API 回归测试 |
| `workflows/prod-smoke-test.yml` | 每日 08:07 UTC 生产冒烟 + VPN 验证 |

### 2.8 `.claude/` — Claude Code 配置

| 内容 | 职责 |
|------|------|
| `settings.local.json` | Claude Code 项目级设置（权限、hooks） |
| `skills/` | 项目级安装的 AI 技能 |

### 2.9 `.agents/` — AI 技能库

| 内容 | 职责 |
|------|------|
| `skills/` | 31 个已安装的 AI 技能（code review、test case design、git guardrails、shadcn 等） |

---

## 3. 根级文档（外部）

以下文档位于仓库根目录，不在 `docs/` 下，但属于关键架构文档：

| 文件 | 说明 |
|------|------|
| `CamelTv-测试自动化平台-建设方案.md` | 顶层架构方案 |
| `测试平台-前后端分离重构方案.md` | v1 → v2 重构设计 |

---

## 4. 如何导航本仓库

### 新人 onboarding 路线

```
1. CLAUDE.md              → 理解项目全景和架构原则
2. docs/business-glossary.md → 掌握统一业务语言
3. docs/repo-map.md        → 建立空间认知（本文档）
4. docs/adr/README.md      → 理解关键架构决策
5. test-platform-v2/CLAUDE.md → 深入主力平台
6. COMMANDS.md             → 跑起来
```

### 按角色导航

| 角色 | 重点关注 |
|------|---------|
| **后端开发者** | `test-platform-v2/backend/` → `test-platform-v2/backend/CLAUDE.md` → `docs/adr/0001` |
| **前端开发者** | `test-platform-v2/frontend/` → `test-platform-v2/frontend/CLAUDE.md` → `docs/adr/0005`、`0006` |
| **测试工程师** | `tests/` → `tests/test-case-standards/` → `test-platform-v2/docs/onboarding.md` |
| **DevOps/CI** | `deploy/` → `Jenkinsfile` → `.github/workflows/` |
| **AI 编码助手** | `CLAUDE.md` 为第一入口 → 按任务涉及模块查阅对应子 CLAUDE.md |

### 按功能导航

| 想做什么 | 去哪里 |
|---------|--------|
| 写功能测试用例 | `tests/test-case-standards/` → `tests/test-cases/functional/` |
| 写接口/API 测试用例 | `tests/api-testing/` |
| 生成测试用例（AI） | `test-platform-v2/backend/app/services/ai_service.py` |
| 配置 CI/CD 流水线 | `Jenkinsfile` + `deploy/jenkins/` + `.github/workflows/` |
| 提取蓝湖原型数据 | `lanhu-mcp/` → `python lanhu_mcp_server.py` |
| 添加新的架构决策 | `docs/adr/template.md` → 创建新 ADR |
| 了解 v1 CLI 工具 | `COMMANDS.md` 第 5 节 + `test-platform/tools/` |
| 部署到测试环境 | `deploy/jenkins/` → Jenkins 自动触发或 `docker compose up -d` |

---

## 5. 与 CLAUDE.md 和 Memory 系统的关系

```
                   ┌─────────────────┐
                   │   CLAUDE.md     │  ← 仓库入口，AI 第一上下文
                   │  (根目录)        │     架构原则 + 快速导航
                   └────────┬────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                  ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ 子 CLAUDE.md │  │  docs/*.md   │  │ Memory 系统  │
   │ (各模块入口)  │  │ (仓库级文档)  │  │ (~/.claude/) │
   └──────────────┘  └──────┬───────┘  └──────┬───────┘
                            │                  │
                            ▼                  ▼
                     ┌──────────────┐  ┌──────────────┐
                     │ 本文档        │  │ 跨会话记忆    │
                     │ repo-map.md  │  │ (偏好+约定)   │
                     └──────────────┘  └──────────────┘
```

| 系统 | 位置 | 生命周期 | 用途 |
|------|------|---------|------|
| **CLAUDE.md 体系** | `f:\CamelTv\CLAUDE.md` + 子模块 `CLAUDE.md` | 随 Git 版本控制 | 项目级 AI 上下文，team 共享 |
| **docs/ 文档** | `f:\CamelTv\docs/` | 随 Git 版本控制 | 仓库级参考文档，team 共享 |
| **Memory 系统** | `~/.claude/projects/f--CamelTv/memory/` | 跨会话持久化 | 个人偏好、约定、速查信息 |

---

## 维护说明

- 新建顶层目录时，在本文档第 2 节新增对应条目
- 新增重要子目录（如新的 API 路由模块）时，更新对应父目录的 `子目录` 表
- 新增 ADR 时，在 2.6 节的 ADR 列表中追加
- 本文档作为仓库锚点，与 CLAUDE.md 和 Memory 系统的 repo-map 保持信息一致
