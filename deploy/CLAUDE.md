---
title: "deploy — CI/CD 部署"
owner: "devops-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["ci-cd", "jenkins", "github-actions", "docker", "deployment"]
related: ["jenkins/README.md", "../test-platform-v2/backend/Dockerfile", "../test-platform-v2/frontend/Dockerfile"]
---

# deploy — CI/CD 部署

> Jenkins Pipeline + GitHub Actions 双通道 CI/CD，Docker Compose 容器化部署。

## 部署架构

```
deploy/
└── jenkins/
    ├── docker-compose.yml    Jenkins Controller + Docker-in-Docker
    ├── Dockerfile            Python 3.12 + Node 18 + Docker CLI 预装
    ├── casc.yaml             Configuration as Code (自动安全配置)
    └── README.md             部署指南

项目根/
├── Jenkinsfile               主 Pipeline 定义 (11 阶段)
├── .github/workflows/        GitHub Actions 定时任务
├── test-platform-v2/deploy/  v2 docker-compose (api-server + web-ui)
├── test-platform/docker-compose.yml  v1 docker-compose (含 WireMock)
└── lanhu-mcp/docker-compose.yml     MCP 服务器部署
```

## Jenkins Pipeline (11 阶段)

```
Checkout → Backend Lint → Backend Test → Frontend TypeCheck → Frontend Test+Build
    → Docker Build → Docker Push (main only) → Deploy Test → Smoke Test → Quality Gate
```

## 环境拓扑

| 环境 | 部署方式 | 触发条件 |
|------|---------|---------|
| **本地开发** | `uvicorn` + `npm run dev` | 手动 |
| **Jenkins 本地** | `docker compose up -d` (deploy/jenkins/) | 手动 |
| **Test** | Jenkins Deploy 阶段自动 | main 分支 push |
| **Staging** | 手动 `docker compose` | 手动 |
| **Prod** | 手动触发 + VPN | 手动 |

## GitHub Actions

| 工作流 | 触发 | 说明 |
|--------|------|------|
| api-regression.yml | 每日 02:03 UTC / 手动 | API 回归测试 |
| prod-smoke-test.yml | 每日 08:07 UTC | 生产冒烟 + VPN 验证 |

## 本地启动 Jenkins

```bash
cd deploy/jenkins
docker compose up -d
# 访问 http://localhost:8080
# 用户名和密码由 deploy/jenkins/.env 注入，禁止写入仓库
```

## Docker 端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| Jenkins | 8080 | CI/CD 控制器 |
| v2 web-ui | 80 | 前端 Nginx |
| v2 api-server | 8000 | FastAPI 后端 |
| WireMock | 8080 (v1) | Mock Server |

## 常用管理命令

```bash
# Jenkins 日志
docker compose -f deploy/jenkins/docker-compose.yml logs -f jenkins

# v2 部署
cd test-platform-v2/deploy
docker compose up -d

# 查看所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## CI/CD 约定

- **Secret 管理**：凭据通过环境变量注入（`.env` 或 Docker secrets），不硬编码在 Jenkinsfile
- **构建产物**：pytest HTML 报告 + JUnit XML，由 Jenkins 发布
- **Git 仓库**：本地开发用 `file:///workspace`（Docker volume 挂载），生产改用远程 Git URL
- **分支策略**：main 分支触发完整 Pipeline（含 Docker Push），其他分支跳过 Push 阶段

## 关联文档

- Jenkins 部署指南：[jenkins/README.md](jenkins/README.md)
- v2 部署：[../test-platform-v2/deploy/README.md](../test-platform-v2/deploy/README.md)
