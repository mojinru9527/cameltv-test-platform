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
Browser :80 → Nginx (frontend container)
                ├── /           → 前端静态文件 (dist/)
                └── /api/*      → 反代 backend:8000
                                    ↓
                              FastAPI (backend container)
                                    ↓
                              SQLite (/data/platform.db, volume)
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
- **端口**：8000 (仅内网 exposed，不对外)
- **健康检查**：`GET /health`，30s 间隔，3 次重试
- **数据**：`tp-data` volume → `/data/platform.db`

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
- ⚠️ `docker compose down -v` 会删除 `tp-data` volume 中的所有数据
- ⚠️ backend 使用 `unless-stopped` 重启策略，异常会自动恢复
- ⚠️ 升级时使用 `docker compose up -d --build` 重新构建镜像

## 关联

- Backend Dockerfile: [../backend/Dockerfile](../backend/Dockerfile)
- Frontend Dockerfile: [../frontend/Dockerfile](../frontend/Dockerfile)
- Jenkins CI/CD: [../../deploy/CLAUDE.md](../../deploy/CLAUDE.md)
- 架构决策: [ADR-0003](../../docs/adr/0003-frontend-backend-physical-separation.md)
