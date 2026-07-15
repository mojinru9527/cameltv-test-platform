---
title: "CamelTv 测试平台 v2（前后端分离重构）"
owner: "qa-team"
last_reviewed: "2026-06-26"
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
├── frontend/    # React 18 + shadcn/ui (Radix + Tailwind) + Vite
└── deploy/      # docker-compose 一键部署
```

## 功能清单与成熟度

> 成熟度标记：✅ 生产可用（真数据/真逻辑）｜🟡 能力有限（可用但关键能力缺）｜🧪 **演示态（数据/结果为随机数模拟，不具生产能力）**

| 模块 | 路由 | 成熟度 | 说明 |
|------|------|--------|------|
| 登录鉴权 / JWT / 项目切换 | `/login` | ✅ | bcrypt + JWT，多项目隔离 |
| 用户/角色/权限 RBAC + 审计日志 | `/system` | ✅ | global/project/self 三级数据范围 |
| 用例服务 CRUD + 域树 | `/testcase` | ✅ | 支持批量操作、域/模块树 |
| 测试计划 + 用例关联 + 执行闭环 | `/testplan` | ✅ | 执行→pass/fail/skip/block，ELK traceId 联动 |
| 工作台看板 | `/workbench` | ✅ | Recharts 图表，按类型/优先级分布 |
| 报告中心 | `/report` | ✅ | JSON 快照，支持 CSV/Excel 导出 |
| 定时任务 (APScheduler) | `/schedule` | ✅ | Cron 表达式校验，手动/定时触发 |
| 需求管理 + AI 生成用例 | `/requirement` | ✅ | MD/Word/Excel/蓝湖上传，DeepSeek LLM 两段式生成+反向评审 |
| 质量追溯矩阵 | `/trace` | ✅ | 项目覆盖率 + 单用例全链路追溯 |
| 缺陷管理 + 内建工作流 | `/defect` | ✅ | 6 状态状态机（open→confirmed→fixing→pending_review→closed/rejected） |
| 通知中心 (Webhook/SMTP) | `/notify` | ✅ | 飞书/钉钉/企微，任务发起/结束/结果通知与发送日志 |
| 项目管理 | `/project` | ✅ | 多项目 + 成员 + 项目级主题 |
| API 测试 | `/apitest` | ✅ | OpenAPI 导入、服务端真实请求、加密环境变量、异步任务和结果快照 |
| UI 自动化 | `/uitest` | ✅ | 服务端真实 Playwright、环境注入、截图/视频/Trace/报告归档 |
| 音视频专项 | `/special` | ✅ | 真实样本记录、ffprobe 帧率探测、统计与阈值判定 |

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI 0.110+ |
| ORM | SQLAlchemy 2.0 |
| 数据库 | SQLite (WAL, 可升 PostgreSQL) |
| 鉴权 | JWT + BCrypt |
| 调度 | APScheduler |
| 前端框架 | React 18 + TypeScript |
| UI | shadcn/ui (Radix UI + Tailwind CSS) |
| 构建 | Vite 5 |
| 部署 | Docker + Nginx |

## 快速启动（本地开发）

### 后端
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端（另开终端）
```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173，使用管理员分配的账号登录。平台不预填或公开通用默认密码。

## 一键部署（Docker）

```bash
cd deploy
cp .env.example .env     # 填写本机密钥和首批账号密码，禁止提交 .env
docker compose up -d     # 访问 http://localhost
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

后端启动后访问 http://localhost:8000/docs (Swagger UI) 或 http://localhost:8000/redoc

## 凭据管理

部署人员通过未跟踪的 `.env` 设置首批账号密码；普通用户由管理员在“系统管理”中创建。真实密码、Token、API Key、Webhook 和 VPN 文件不得提交到 Git。
