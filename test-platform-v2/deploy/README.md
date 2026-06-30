# CamelTv 测试平台 v2 — Docker 部署指南

## 前置要求

- Docker 20.10+
- Docker Compose v2

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env：修改 SECRET_KEY 为随机字符串

# 2. 启动全栈
docker compose up -d

# 3. 验证
curl http://localhost/health   # 后端健康检查
# 浏览器打开 http://localhost
```

## 默认凭据

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 超级管理员 | admin | admin123 |
| 测试人员 | tester | tester123 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | `please-change-me...` | JWT 签名密钥，生产必换 |
| `FRONTEND_PORT` | `80` | 前端访问端口 |
| `ALLOWED_ORIGINS` | `*` | CORS 允许的来源 |
| `ELK_BASE_URL` | (空) | Kibana 地址，用于 traceId 链路 |
| `ELK_INDEX` | `*` | ELK 索引 pattern |

## 常用命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 重启
docker compose restart

# 停止
docker compose down

# 停止并清除数据
docker compose down -v
```

## 数据持久化

- 数据库文件 `platform.db` 存储在 Docker volume `tp-data` 中
- 使用 `docker compose down -v` 会**永久删除**所有数据

## 升级

```bash
git pull
docker compose up -d --build
```

## 排障

**端口被占用**：修改 `.env` 中 `FRONTEND_PORT` 为其他端口

**后端启动失败**：查看日志 `docker compose logs backend --tail 50`

**数据库错误**：删除 volume 重建 `docker compose down -v && docker compose up -d`
