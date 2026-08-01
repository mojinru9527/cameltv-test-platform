---
title: "CamelTv 测试平台 v2（前后端分离重构）"
owner: "qa-team"
last_reviewed: "2026-08-01"
status: "active"
expires: "2026-12-26"
tags: ["test-platform", "v2", "fullstack", "fastapi", "react"]
related: ["test-platform-v2/backend/README.md", "test-platform-v2/frontend/README.md", "test-platform-v2/docs/CamelTv测试平台-完整PRD.md"]
---

# CamelTv 测试平台 v2（前后端分离重构）

> 按《测试平台-前后端分离重构方案 v2.1》搭建的全新项目，与重构前的 `../test-platform/` 物理隔离。

## 架构

```
test-platform-v2/
├── backend/     # FastAPI + SQLAlchemy + SQLite
├── frontend/    # React 19 + shadcn/ui (Radix + Tailwind) + Vite
└── deploy/      # docker-compose 一键部署
```

## 功能清单与成熟度

> 成熟度只描述当前证据，不等同于生产放行：✅ 为本地受控链路已验证；🟡 为真实实现但验收不完整；⛔ 为缺外部条件或明确延期。Batch 60 总结论仍是 `NEEDS WORK`，production 发布仍是 `DEFERRED`。

| 模块 | 路由 | 成熟度 | 当前事实 |
|------|------|--------|----------|
| 登录、项目、系统管理 | `/login` `/project` `/system` | 🟡 | bcrypt + JWT；浏览器以 httpOnly Cookie 会话为主，Bearer 仅作过渡回退；全模块三身份 RBAC/项目隔离矩阵与强制改密门禁仍待完成 |
| 工作台、用例、计划、报告、缺陷、定时、追溯 | `/workbench` `/testcase` `/testplan` `/report` `/defect` `/schedule` `/trace` | 🟡 | 本地真实 CRUD/状态流/审计主链已验证，但跨页查询、全路由权限、响应式和无障碍验收尚未完整 |
| 需求、脑图、知识、Agent、发布包 | `/requirement` `/mindmap` `/knowledge` `/agent-workbench` `/release-bundles` | 🟡 / ⛔ | 本地持久化链存在；真实 LLM、蓝湖、Wiki 等依赖缺授权凭据时必须 fail closed，不能据本地回归宣称外部链路通过 |
| API 测试 | `/apitest` | 🟡 | OpenAPI/Swagger 预览与导入、httpx 真实执行、任务和快照已实现；五入口一致性、生产保护、当前 Test5 六服务契约与业务回归仍待验收 |
| UI 自动化 | `/uitest` | 🟡 | 本地 Runner 可启动真实 Playwright 并持久化结果/产物；这不等于 `tests/automation/ui/` 的体育 Test5/生产业务 E2E 已通过 |
| 音视频专项 | `/special` | 🟡 | 已有真实媒体样本与 ffprobe 指标链；外部真实流、设备和完整发布矩阵仍未覆盖 |
| 环境、数据集、通知、集成 | `/environment` `/dataset` `/notify` `/integration` | 🟡 / ⛔ | 本地数据模型和错误路径可用；SMTP/Webhook/Jira/TAPD/ELK 等真实链路缺非生产端点与凭据时保持阻塞 |
| 性能监控 | `/perftest` | ⛔ | 服务可 fail closed；缺 SoloX、授权真机和采集窗口，不能标为已验收 |
| 运维发布控制 | 独立项目，无产品路由 | ⛔ | Batch 61 在 `deploy/release-control/` 建设 test-only 领域库/CLI；production adapter 明确拒绝，控制面 API/UI 属于 Batch 62 |

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI 0.140.13（`requirements.lock`；声明下限 `>=0.110`） |
| ORM | SQLAlchemy 2.0.51（`requirements.lock`） |
| 数据库 | SQLite (WAL, 可升 PostgreSQL) |
| 鉴权 | BCrypt + JWT；httpOnly Cookie 主会话，Bearer 兼容回退 |
| 调度 | APScheduler |
| 前端框架 | React 19.2.8 + React Router 8.3.0 + TypeScript 5.6 |
| UI | shadcn/ui (Radix UI + Tailwind CSS) |
| 构建 | Vite 7.3.6 |
| 部署 | Docker + Nginx |

## 快速启动（本地开发）

### 固定环境入口

测试平台自身只采用两套独立实例，不在页面内热切数据库。浏览器地址即环境，
每个实例只连接自己的数据库：

| 环境 | 固定入口 | 数据库 | 启动方式 |
|------|----------|--------|----------|
| local | `http://localhost:5173` | 独立 SQLite `platform-local.db` | `scripts/start-platform-environment.ps1` |
| production | **未部署；保留独立 profile 身份** | 未来独立生产 PostgreSQL | 服务器采购后再配置并显式确认启动 |

当前只初始化 local。production 的模板用于锁定未来实例与 local 的隔离契约，
不是可访问地址；在服务器、域名、TLS 和 PostgreSQL 就绪前不创建
`production.env`，也不启动 production。

```powershell
# 首次运行：安全生成受 Git 忽略的 local.env 和固定本地凭据
pwsh scripts/start-platform-environment.ps1 `
  -Target local -Action start -InitializeLocal

# 后续运行
pwsh scripts/start-platform-environment.ps1 -Target local -Action start
```

> 页面 `/environment` 管理的是**被测系统**的 dev/test/staging/prod 地址和
> 变量，不会也不应切换测试平台自身的数据库。

### 后端
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.lock
uvicorn app.main:app --reload --port 8000
```

### 前端（另开终端）
```bash
cd frontend
npm ci
npm run dev
```

浏览器打开 http://localhost:5173，使用管理员分配的账号登录。平台不预填或公开通用默认密码。

## 未来生产部署（Docker）

当前生产服务器尚未采购，以下命令不属于 Batch 57 的当前操作步骤。只有在
服务器、域名、TLS、PostgreSQL、备份和回滚窗口均已确认后才执行：

```bash
cd deploy
cp ../config/runtime/production.env.example ../config/runtime/production.env
# 一次性填写生产环境的密钥、HTTPS 来源和 PostgreSQL 密码
pwsh ../scripts/start-platform-environment.ps1 \
  -Target production -Action start -ConfirmProduction
```

详见 [deploy/README.md](deploy/README.md)

## CI/CD（Jenkins 自动化构建）

### 一键启动 Jenkins

```bash
cd ..\deploy\jenkins
docker compose up -d
```

首次启动约 3~5 分钟（拉取镜像 + 构建 + 自动配置）。

### 访问

```
浏览器打开 http://localhost:8080
用户名和密码由 `deploy/jenkins/.env` 注入，不保存在仓库中。
```

Jenkins 已通过 CasC 自动完成安全配置——跳过安装向导和插件安装。

首次登录后创建一个 **Pipeline Job**：`New Item` → `Pipeline` → SCM 选 Git，URL 填 `file:///workspace`，Script Path 填 `Jenkinsfile`。

Pipeline 流程：Checkout → Backend Lint → Backend Test(pytest) → Frontend TypeCheck → Frontend Test+Build → Docker Build → Deploy → Smoke Test → Quality Gate

详见 [deploy/jenkins/README.md](../deploy/jenkins/README.md)

## 使用与接入指南

新项目接入流程：[docs/onboarding.md](docs/onboarding.md)

完整用户与管理员手册：[docs/测试平台使用手册.md](docs/测试平台使用手册.md)

## API 文档

后端由 FastAPI 运行时生成 OpenAPI：`/openapi.json`、`/docs`（Swagger UI）和 `/redoc`。业务路由统一位于 `/api/v1`，健康检查位于 `/health`。前端类型需在后端契约可访问时显式运行 `npm run gen:api` 生成，仓库中的生成文件不能替代运行时契约核对。

API 测试资产导入支持 OpenAPI 3.x 与 Swagger 2.0 的 JSON/YAML 文本或 URL，并提供预览/确认流程；Knife4j/Swagger 文档 URL 作为来源类型记录。该导入能力只证明契约解析与资产入库，不代表当前 Test5 六服务或生产接口已经执行通过。

## UI 自动化证据边界

- `backend/tests/playwright/specs/` 是测试平台 UI Runner 的本地 smoke 资产，验证 Runner、浏览器、状态和产物闭环。
- `tests/automation/ui/` 是体育用户端/运营后台业务 E2E 资产，必须在获授权的 Test5/生产只读目标上以当前契约、账号和稳定数据单独执行。
- 脚本可收集、本地 Runner 绿色、历史截图或历史接口数量，均不能换算成体育业务 E2E 通过。

## 运维发布项目边界

Batch 61 运维发布 MVP 是仓库内独立项目 `deploy/release-control/`，提供不可变 manifest、test-only 发布状态机、Jenkins/Compose 适配、回滚和防篡改证据；它不是 `test-platform-v2` 的新页面。Batch 61 不配置 production 发布，生产目标必须返回 `PRODUCTION_NOT_CONFIGURED`；控制面 API/UI 延后到 Batch 62。

## 凭据管理

部署人员通过未跟踪的 `.env` 设置首批账号密码；普通用户由管理员在“系统管理”中创建。真实密码、Token、API Key、Webhook 和 VPN 文件不得提交到 Git。
