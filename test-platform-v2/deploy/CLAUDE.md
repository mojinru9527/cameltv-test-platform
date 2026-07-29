---
title: "test-platform-v2/deploy — Docker 部署上下文"
owner: "devops-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["deploy", "docker", "nginx", "devops"]
related: ["../backend/CLAUDE.md", "../frontend/CLAUDE.md", "../../deploy/CLAUDE.md", "../../docs/adr/0003-frontend-backend-physical-separation.md"]
---

# test-platform-v2/deploy — Docker 部署

> v2 测试平台的 Docker Compose 一键部署方案。Nginx 反代前端静态文件 + 后端 API。

## 架构

```
Browser HTTPS → TLS gateway → Nginx :80 (frontend container)
                ├── /           → 前端静态文件 (dist/)
                └── /api/*      → 反代 backend:8000
                                    ↓
                              FastAPI (backend container)
                                    ↓
                              PostgreSQL (pg-data volume)
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 服务编排 — backend + frontend + volume |
| `.env.example` | 环境变量模板（SECRET_KEY, FRONTEND_PORT 等） |
| `README.md` | 快速开始指南 + 排障 |

## 服务说明

### backend 容器
- **镜像**：`../backend/Dockerfile`
- **构建上下文**：仓库根目录；由根 `.dockerignore` 排除依赖、测试结果、
  VCS 元数据和本地 Agent 元数据
- **端口**：8000 (仅内网 exposed，不对外)
- **健康检查**：`GET /health`，30s 间隔，3 次重试
- **数据库**：PostgreSQL `pg-data` volume；`DATABASE_URL` 必填
- **验收产物**：`tp-artifacts` volume → `/app/storage`（UI runner + 蓝湖证据）
- **执行器运行时**：Node/npm + npm 锁定的 Playwright Chromium +
  Python Playwright + ffmpeg/ffprobe
- **蓝湖 Provider**：复制根仓固定子模块的运行模块到 `/app/lanhu-mcp`；
  下载缓存位于 `/data/lanhu`
- **运行身份**：`cameltv`，固定 UID/GID `10001:10001`；Python 环境位于
  `/opt/venv`，不依赖 `/root/.local`

### frontend 容器
- **镜像**：`../frontend/Dockerfile` (Nginx + 构建产物)
- **端口**：80 (映射到宿主机 `${FRONTEND_PORT}`)
- **依赖**：wait for backend healthy 后启动
- **健康检查**：`nginx -t`

## 部署命令

```bash
# 准备环境变量
cp .env.example .env
# 务必修改 SECRET_KEY

# 启动
docker compose up -d

# 验证
curl http://localhost/health
```

## 关键注意事项

- ⚠️ `SECRET_KEY` 生产务必使用强随机值：`python -c "import secrets; print(secrets.token_urlsafe(32))"`
- ⚠️ `docker compose down -v` 会删除 `tp-data`、`tp-artifacts` 和 `pg-data`
  中的数据库及验收产物
- ⚠️ backend 使用 `unless-stopped` 重启策略，异常会自动恢复
- ⚠️ 升级时使用 `docker compose up -d --build` 重新构建镜像
- ⚠️ Chromium 和系统依赖会使 backend 镜像增加数百 MB；实际体积必须在
  完整构建后用 `docker image inspect` 记录
- ⚠️ Chromium/ffmpeg 只解除 UI Runner、蓝湖截图和媒体基础探测的运行时
  缺失；真实 OCR 引擎、ADB、设备权限和 SoloX 仍需独立部署与验收
- ⚠️ `volume-permissions` 会在 backend 前以 root 运行一次，只对两个命名
  volume 的固定挂载点修复 UID/GID；不得扩展到任意宿主机路径

## 构建契约

- 根仓必须先初始化 `lanhu-mcp` 子模块。
- UI Runner 依赖只允许 `npm ci`；不得用 `npm install` 作为失败回退。
- Python Playwright 在镜像构建时对齐 `package-lock.json` 中的 Playwright
  版本，并与 Node Runner 共用 `/ms-playwright`。
- 所有系统包、npm/Python 依赖和 Chromium 必须在最终 `USER` 之前安装；
  最终运行用户必须为 `cameltv:cameltv`。
- `/app`、`/data`、`/ms-playwright`、`/app/storage` 和用户 cache 必须在
  镜像中归属 UID/GID `10001:10001`，Compose 不得覆盖为 root。
- 部署静态检查使用仓库根目录执行
  `docker build --check -f test-platform-v2/backend/Dockerfile .`。
- Compose 检查使用 `docker compose config --quiet` 和
  `docker compose build --check backend`；未完整构建时不得声称运行时探针通过。
- Compose 固定生产模式、Secure Cookie 和禁用 `create_all`；必须通过 HTTPS
  入口使用，并且启动迁移必须确认唯一 Alembic head。

## 关联

- Backend Dockerfile: [../backend/Dockerfile](../backend/Dockerfile)
- Frontend Dockerfile: [../frontend/Dockerfile](../frontend/Dockerfile)
- Jenkins CI/CD: [../../deploy/CLAUDE.md](../../deploy/CLAUDE.md)
- 架构决策: [ADR-0003](../../docs/adr/0003-frontend-backend-physical-separation.md)
