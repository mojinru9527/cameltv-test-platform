---
name: cameltv-deploy
description: Use when asked to deploy, release, or update environments — "部署到test", "发布到staging", "构建Docker镜像", "触发Jenkins", "启动服务", "docker compose up". Covers the full CamelTv CI/CD deployment pipeline across test/staging/prod environments.
---

# CamelTv 部署

## Overview

管理 CamelTv 项目的容器化部署，覆盖 test / staging / prod 三个环境。Jenkins Pipeline（11 阶段）与 GitHub Actions 双通道 CI/CD。

**核心原则：先验证环境连通性，再执行部署；部署后必须冒烟测试。**

## 何时使用

- 用户说「部署到 test」「发布到 staging」「上线」「构建镜像」
- 需要启动本地开发环境（docker compose up）
- 查看/排查部署状态
- 配置新的环境或服务

## 环境拓扑

| 环境 | 部署方式 | 触发条件 | VPN |
|------|---------|---------|-----|
| localhost | 手动 `docker compose up -d` | 本地开发 | 不需要 |
| test | Jenkins 自动部署 | push main 分支 | 不需要 |
| staging | 手动触发 | workflow_dispatch | 不需要 |
| prod | 手动触发 | workflow_dispatch | ✅ 需要 VPN |

## 服务组件

```
                    ┌──────────────┐
                    │   Nginx:80   │ ← 前端静态文件 + 后端反代
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
     │ Backend:8000│ │Frontend  │ │ lanhu-mcp  │
     │  FastAPI    │ │  static  │ │  :8000     │
     └──────┬──────┘ └──────────┘ └────────────┘
            │
     ┌──────▼──────┐
     │  SQLite DB  │
     │  (WAL mode) │
     └─────────────┘
```

## 强制工作流程

### 第 1 步：确认目标环境

- 检查环境连通性（prod 需先验证 VPN 连接 `vpn07`）。
- 查看对应环境变量文件（`.env` / `.env.production`）。
- 确认当前分支和目标环境匹配。

### 第 2 步：部署前检查

```bash
# 检查 Docker 状态
docker info

# 检查端口占用（避免冲突）
# Windows:
netstat -ano | findstr "80 8000 5173"
# Unix:
lsof -i :80 -i :8000 -i :5173

# 检查磁盘空间
df -h  # Unix
```

端口占用速查表：

| 端口 | 服务 |
|------|------|
| 80 | Nginx (v2 deploy) |
| 8000 | Backend FastAPI / lanhu-mcp |
| 8080 | Jenkins Controller |
| 5173 | Frontend Vite dev server |
| 9222 | Playwright CDP (lanhu-mcp) |

### 第 3 步：选择部署方式

#### 方式 A：v2 一键部署（推荐）

```bash
cd test-platform-v2/deploy

# 准备环境变量
cp .env.example .env
# 修改 SECRET_KEY（生产环境务必使用随机值）
# openssl rand -hex 32

# 拉取并启动
docker compose pull        # 拉取最新镜像（如果使用 registry）
docker compose up -d       # 后台启动

# 验证
curl -s http://localhost/health
```

#### 方式 B：Jenkins Pipeline

触发 Jenkins 构建：
1. 进入 Jenkins Dashboard（`http://localhost:8080`，如果本地运行）
2. 选择「CamelTv Pipeline」→「Build with Parameters」
3. 设置参数：
   - `DEPLOY_ENV`: test / staging / prod
   - `RUN_TESTS`: true（推荐）
   - `DOCKER_BUILD`: true
   - `DEPLOY`: true

#### 方式 C：仅构建 Docker 镜像（不部署）

```bash
# 后端镜像
cd test-platform-v2/backend
docker build -t cameltv-tp-backend:latest -f Dockerfile .

# 前端镜像
cd test-platform-v2/frontend
docker build -t cameltv-tp-frontend:latest -f Dockerfile .
```

#### 方式 D：Jenkins 本地开发环境

```bash
cd deploy/jenkins
docker compose up -d        # 启动 Jenkins Controller
# 访问 http://localhost:8080
# 初始 admin 密码：docker exec cameltv-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 第 4 步：冒烟验证

部署后立即执行冒烟测试：

```bash
# 健康检查
curl -s http://localhost/health

# 登录 API
curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"${E2E_USERNAME}","password":"${E2E_PASSWORD}"}'

# 前端可访问
curl -s -o /dev/null -w '%{http_code}' http://localhost/
# 期望：200
```

## 回滚

如果部署后发现问题：

```bash
# Docker Compose 回滚到上一版本
docker compose down
IMAGE_TAG=<上一个正常版本> docker compose up -d

# 或使用 Git revert
git revert HEAD --no-edit
git push origin main  # 触发 Jenkins 重新构建
```

## 常见问题速查

| 症状 | 可能原因 | 排查 |
|------|---------|------|
| 后端 502 Bad Gateway | Backend 未启动或端口错误 | `docker compose ps`、`docker logs cameltv-backend` |
| 前端白屏 | Nginx 配置或前端构建产物路径错误 | `docker logs cameltv-nginx` |
| 端口冲突 | 其他进程占用 80/8000 | `netstat -ano \| findstr "80"` |
| 数据库 locked | SQLite 并发写入冲突（v2 已用 WAL 大幅缓解） | 等待或重启 backend |
| VPN 不通 | prod 环境需 vpn07 | 检查 VPN 连接状态 |

## 注意事项

- ⚠️ **生产部署前务必确认 VPN 连接**（见 [memory: env-urls](../../../memory/env-urls.md)）。
- ⚠️ **不要在生产环境使用 `.env.example` 的默认密钥**——`openssl rand -hex 32` 生成新密钥。
- ⚠️ **Jenkins 并发构建**可能导致 Docker 镜像 tag 冲突——等待上一次构建完成。
- ⚠️ **Docker-in-Docker** (Jenkins) 模式下磁盘空间容易不足，定期清理 `docker system prune`。

## 关联

- Jenkinsfile（根目录）：11 阶段 CI/CD Pipeline 定义
- [deploy/jenkins/](../../../deploy/jenkins/)：Jenkins 本地开发环境
- [deploy/CLAUDE.md](../../../deploy/CLAUDE.md)：CI/CD 架构概述
- [docs/adr/0003-frontend-backend-physical-separation.md](../../../docs/adr/0003-frontend-backend-physical-separation.md)：前后端独立部署决策
