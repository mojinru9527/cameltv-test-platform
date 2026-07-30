---
title: "Batch 58 Design Spec — 生产基础设施云注册"
owner: "design-team"
created: "2026-07-30"
status: "active"
batch: "58"
tags: ["design", "production", "cloudflare", "vercel", "supabase", "batch-58"]
---

# Batch 58 Design Spec: 生产基础设施云注册

## 1. 目标架构

```
                         ┌──────────────────────────┐
                         │   Cloudflare DNS / CDN    │
                         │   cameltv-platform.com    │
                         │   SSL: Full (strict)      │
                         └─────┬────────────┬────────┘
                               │            │
                    CNAME      │            │ A/CNAME
                               ▼            ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│  Vercel                  │   │  Backend Server (TBD)    │
│  Frontend: React 19      │   │  FastAPI + Uvicorn       │
│  Build: Vite 7           │   │  Port: 8000              │
│  Domain: <p>.vercel.app  │   │  /api/* endpoints        │
└──────────────────────────┘   └──────────┬───────────────┘
        │                                 │
        │  /api/* (rewrite)               │  DATABASE_URL
        └─────────────────────────────────┤
                                          ▼
                               ┌──────────────────────────┐
                               │  Supabase PostgreSQL 16  │
                               │  PgBouncer :6543         │
                               │  Region: ap-southeast-1  │
                               └──────────────────────────┘
```

## 2. 组件设计

### 2.1 Vercel 前端部署

**文件**: `test-platform-v2/frontend/vercel.json`

```json
{
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "nodeVersion": "22.x",
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://<backend>/api/:path*" },
    { "source": "/((?!api/).*)", "destination": "/index.html" }
  ]
}
```

**设计决策**:
- 使用 Vercel Rewrites 而非 Nginx 反代 → 前端容器不再需要 Nginx
- SPA fallback 使用正则排除 `/api/` → 与现有 nginx.conf 行为一致
- API 反代目标为后端服务器公网 URL → 待后端托管方案确定

### 2.2 Cloudflare DNS

**文件**: `test-platform-v2/deploy/cloudflare-dns-records.md`

**DNS Records**:

| Type | Name | Target | Proxy | TTL |
|------|------|--------|-------|-----|
| CNAME | `@` | `<project>.vercel.app` | ✅ Proxied | Auto |
| CNAME | `api` | `<backend-host>` | ✅ Proxied | Auto |
| CNAME | `www` | `@` | ✅ Proxied | Auto |

**SSL/TLS**: Full (strict) — Cloudflare ↔ Origin 使用加密连接

### 2.3 Supabase PostgreSQL

**文件**: `test-platform-v2/deploy/supabase-setup.md`

**连接配置**:
```
Host: <project-ref>.supabase.co
Port: 6543 (PgBouncer — 连接池)
Database: cameltv_production
User: cameltv
SSL: require
```

**Alembic 迁移**:
- 使用现有 Alembic 配置 (`test-platform-v2/backend/alembic/`)
- 迁移命令: `DATABASE_URL="<supabase-uri>" alembic upgrade head`
- 需在 Supabase Dashboard 开启 Network Restrictions 或保持开放

### 2.4 后端部署（待定）

当前后端 (FastAPI) 仍需独立托管。可选方案：

| 方案 | 改动量 | 成本 | 推荐 |
|------|-------|------|------|
| A) 现有 VPS + Docker (backend only) | 小 | 现有 | ⭐ 推荐 |
| B) Railway.app | 中 | ~$5/mo | 备选 |
| C) Render.com | 中 | 免费层有限 | 备选 |

## 3. 配置文件清单

| # | 文件 | 用途 | 状态 |
|---|------|------|------|
| 1 | `test-platform-v2/frontend/vercel.json` | Vercel 部署配置 | ✅ 已创建 |
| 2 | `test-platform-v2/deploy/cloudflare-dns-records.md` | Cloudflare DNS 配置 | ✅ 已创建 |
| 3 | `test-platform-v2/deploy/supabase-setup.md` | Supabase 数据库配置 | ✅ 已创建 |
| 4 | `test-platform-v2/deploy/production-architecture.md` | 生产架构总览 | ✅ 已创建 |
| 5 | `test-platform-v2/config/runtime/production.env` | 生产运行环境变量 | ✅ 已创建 |
| 6 | `test-platform-v2/docs/Batch58生产基础设施注册操作单.md` | 注册操作指南 | ✅ 已创建 |

## 4. 与现有系统集成

### 不改动的部分
- ✅ `test-platform-v2/backend/` — FastAPI 代码不变
- ✅ `test-platform-v2/frontend/src/` — React 代码不变
- ✅ `test-platform-v2/deploy/docker-compose.yml` — 保持不变，仍可用于自建部署
- ✅ `test-platform-v2/backend/alembic/` — 迁移脚本不变
- ✅ `test-platform-v2/config/runtime/production.env.example` — 模板不变

### 新增的部分
- ➕ `vercel.json` — Vercel 部署描述
- ➕ `production.env` — 真实生产环境变量（gitignored）
- ➕ 三个平台注册文档

## 5. 安全设计

| 层面 | 措施 |
|------|------|
| 传输 | Cloudflare SSL Full (strict) + Supabase SSL required |
| 秘密 | `production.env` gitignored，密码不入仓库 |
| CDN | Cloudflare Proxy 隐藏源站 IP |
| 数据库 | Supabase Network Restrictions / PgBouncer 连接池 |
| 前端 | Vercel 自动 HTTPS，环境变量加密存储 |
