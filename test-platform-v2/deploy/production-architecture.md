---
title: "生产环境部署架构 — Batch 58 Cloud-Registered"
owner: "devops-team"
created: "2026-07-30"
status: "draft"
tags: ["production", "architecture", "cloudflare", "vercel", "supabase", "batch-58"]
---

# 生产环境部署架构 (Batch 58)

## 架构概览

```
                         ┌──────────────────────┐
                         │   Cloudflare DNS/CDN │
                         │   (域名解析 + HTTPS)  │
                         └──────┬───────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼                               ▼
┌───────────────────────┐           ┌──────────────────────┐
│  Vercel (前端托管)     │           │  后端服务器 (TBD)     │
│  React 19 + Vite 7    │           │  FastAPI + Uvicorn   │
│  SPA + /api 反代      │           │  :8000               │
└───────────────────────┘           └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │  Supabase PostgreSQL │
                                    │  v16, PgBouncer:6543 │
                                    └──────────────────────┘
```

## 组件

### Cloudflare — DNS + CDN
- **用途**: 域名 DNS 解析、HTTPS/TLS 终结、CDN 缓存
- **配置**: DNS CNAME → Vercel; A/CNAME → 后端服务器
- **SSL**: Full (strict)
- **文档**: `deploy/cloudflare-dns-records.md`

### Vercel — Frontend Hosting
- **用途**: React 前端构建 + 静态托管 + /api 反代
- **配置**: `frontend/vercel.json`
- **框架**: Vite 7
- **Node**: 22.x
- **部署域名**: `cameltv-test-platform1.vercel.app` ✅
- **文档**: `frontend/vercel.json`

### Supabase — PostgreSQL Database
- **用途**: 生产数据库 (替代自托管 PostgreSQL 容器)
- **版本**: PostgreSQL 16
- **Project Ref**: `myhwdpjmxdsodqgeecpn` ✅
- **连接池**: PgBouncer `aws-0-ap-southeast-1.pooler.supabase.com:6543`
- **迁移工具**: Alembic
- **文档**: `deploy/supabase-setup.md`

### Backend (待定)
- **当前状态**: 需要独立托管方案
- **选项**:
  - A) 现有 VPS + Docker Compose (仅 backend + postgres 服务)
  - B) Railway / Render / Fly.io 托管 FastAPI
  - C) Cloudflare Workers (需要重写为 JS/TS)
- **推荐**: 选项 A (最小改动)，将 backend Docker 容器部署到 VPS，
  去除 frontend 和 postgres 服务 (分别由 Vercel 和 Supabase 替代)

## 与旧架构对比

| 组件 | 旧 (Docker Compose) | 新 (Batch 58) | 变更 |
|------|-------------------|---------------|------|
| 前端托管 | Nginx 容器 (自建) | Vercel | 托管化 |
| 数据库 | PostgreSQL 容器 (自建) | Supabase | 托管化 |
| DNS/CDN | 无/手动 | Cloudflare | 新增 |
| 后端 | FastAPI 容器 | TBD (VPS/Railway) | 待定 |
| TLS | Nginx/手动 | Cloudflare + Vercel 自动 | 自动化 |

## 注册顺序

1. **Supabase** — 先创建数据库项目，获得连接串
2. **Vercel** — 导入前端项目，配置环境变量
3. **Cloudflare** — 配置 DNS 指向 Vercel 和后端
4. **Backend** — 部署后端并配置 Supabase 连接
