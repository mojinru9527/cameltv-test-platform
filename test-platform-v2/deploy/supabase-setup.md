---
title: "Supabase PostgreSQL Setup — CamelTv 测试平台生产环境"
owner: "devops-team"
created: "2026-07-30"
status: "draft"
tags: ["supabase", "postgresql", "production", "batch-58"]
---

# Supabase PostgreSQL — 测试平台生产数据库

> ⚠️ 本文档中的连接参数为占位符。注册 Supabase 并创建项目后回填真实值。

## 1. 数据库参数规划

| 参数 | 当前占位值 | 注册后回填 |
|------|----------|----------|
| PostgreSQL 版本 | 16 | Supabase 默认 16 |
| 数据库名 | `cameltv_production` | Supabase 项目默认 `postgres` |
| Schema | `public` | `public` |
| 用户名 | `cameltv` | Supabase 项目用户 |
| 密码 | `change-me-production-postgres` | Supabase 项目密码 |
| 主机 | `postgres` (容器名) | `<project-ref>.supabase.co` |
| 端口 | `5432` | `6543` (Supabase 连接池) 或 `5432` |
| 连接池 | `10` + `20` overflow | 使用 Supabase PgBouncer (`6543`) |

## 2. Supabase 注册步骤

1. 访问 https://supabase.com/dashboard/sign-up 注册账号
2. 创建新项目 (New Project)
   - Organization: 默认或新建
   - Name: `cameltv-platform` (或自定义)
   - Database Password: 生成强密码 (>=16 字符，含大小写+数字+符号)
   - Region: 选择离用户最近的区域 (推荐 Southeast Asia / Singapore)
   - Pricing Plan: Free (500 MB database, 2 GB bandwidth)
3. 等待项目创建完成 (~2 分钟)
4. 进入 Settings → Database → Connection string
5. 复制连接字符串（选择 `psql` 或 `URI` 格式）

## 3. Alembic 迁移配置

Supabase 项目创建后，在 `production.env` 中配置:

```env
DATABASE_URL=postgresql://cameltv:<password>@<project-ref>.supabase.co:6543/cameltv_production
DB_POOL_SIZE=8
DB_MAX_OVERFLOW=16
```

然后运行迁移:

```bash
cd test-platform-v2/backend
alembic upgrade head
```

## 4. 注册后回填 (已完成 2026-07-30)

| 字段 | 值 |
|------|-----|
| Supabase 账号 | GitHub OAuth (`mojinru9527`) |
| Supabase 项目名 | `cameltv-platform` |
| Supabase Project Ref | `myhwdpjmxdsodqgeecpn` |
| 数据库连接串 (Pooler) | `postgresql://postgres.myhwdpjmxdsodqgeecpn:<password>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres` |
| Region | Southeast Asia (Singapore) |
| PostgreSQL 版本 | `16` |
| 密码状态 | ⚠️ 待用户填入 `production.env` |

⚠️ **安全提示**: 数据库密码和完整连接串不要写入 Git 仓库。
只通过 `test-platform-v2/config/runtime/production.env` 注入（该文件已 .gitignore）。
