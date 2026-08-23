---
title: "Batch 58 生产基础设施注册操作单 — Cloudflare / Vercel / Supabase"
owner: "devops-team"
created: "2026-07-30"
status: "active"
tags: ["batch-58", "production", "cloudflare", "vercel", "supabase", "registration"]
---

# Batch 58 生产基础设施注册操作单

> ⚠️ **已迁移/退役（2026-08-22 → swiftbugs.cn）**：本操作单描述 2026-07-30 注册 Vercel/Cloudflare/Supabase 的历史流程，仅作存档；当前生产为腾讯云广州单机 https://swiftbugs.cn（ICP 粤ICP备2026121122号-1），部署/运维见 docs/ops/tencent-cloud-migration.md。

> 三个平台均需浏览器交互注册。以下为逐步操作指南。

## 0. 前置准备

在开始注册前准备：
- [ ] 可接收验证邮件的邮箱
- [ ] GitHub 账号（用于 Vercel 和 Supabase 快速登录）
- [ ] 一个域名（如 `cameltv-platform.com` 或 `platform.cameltv.live`），或使用平台提供的免费子域名
- [ ] 密码管理器（生成并保管强密码）

## 1. Supabase (PostgreSQL 数据库) — 先注册

> **优先级最高**: 数据库创建后立即获得连接串，供 Vercel 环境变量配置使用。

**注册步骤**:
1. 浏览器打开 https://supabase.com/dashboard/sign-up
2. 选择 **Continue with GitHub**（推荐，与仓库同一账号）
3. 授权后进入 Dashboard → **New Project**
4. 填写:
   - Name: `cameltv-platform`
   - Database Password: 点击 Generate 生成强密码 → **务必保存到密码管理器**
   - Region: 选择 **Southeast Asia (Singapore)** 或 **Asia Pacific**
   - Pricing: **Free Plan** ($0/month)
5. 点击 **Create Project**，等待 1-3 分钟

**获取连接串**:
1. 进入 Project → Settings → Database
2. 找到 **Connection string** 区段
3. 选择 **URI** 格式
4. 复制连接串（格式: `postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres`）
5. 数据库名默认 `postgres`，可通过 `ALTER DATABASE` 或新创建改为 `cameltv_production`

**回填到 `production.env`**:
```
DATABASE_URL=<复制的连接串>
POSTGRES_PASSWORD=<你的Supabase数据库密码>
```

**运行 Alembic 迁移** (需要 Python 环境):
```bash
cd test-platform-v2/backend
DATABASE_URL="<supabase连接串>" alembic upgrade head
```

## 2. Vercel (前端部署) — 第二注册

**注册步骤**:
1. 浏览器打开 https://vercel.com/signup
2. 选择 **Continue with GitHub**（与仓库同一账号）
3. 授权 Vercel 访问 GitHub 仓库
4. 进入 Dashboard → **Add New → Project**
5. 选择仓库: `mojinru9527/cameltv-test-platform`
6. 配置:
   - Root Directory: `test-platform-v2/frontend`
   - Framework Preset: **Vite**
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm ci`
7. 展开 **Environment Variables**:
   - `VITE_PROXY_TARGET`: 留空或设为后端 URL
   - 其他变量根据后端需要添加
8. 点击 **Deploy**

**自动 Git 集成**:
- Vercel 自动创建 GitHub 集成，每次 push 到 main 自动部署
- 可在 Vercel Dashboard → Settings → Git 配置
- 建议开启 **Preview Deployments**（PR 自动预览）

**获取部署域名**:
- 部署成功后 Vercel 分配 `<project-name>.vercel.app` 子域名
- 回填到 `production.env` 的 `PLATFORM_FRONTEND_URL`

## 3. Cloudflare (DNS + CDN) — 第三注册

**注册步骤**:
1. 浏览器打开 https://dash.cloudflare.com/sign-up
2. 使用邮箱注册（需要验证）
3. 进入 Dashboard → **Add a Site**
4. 输入你的域名（如 `cameltv-platform.com`）
5. 选择 **Free Plan** ($0/month)
6. Cloudflare 自动扫描现有 DNS Records
7. **更新域名 DNS 服务器**: 在你的域名注册商处，将 NS 记录更换为 Cloudflare 提供的两个 NS 地址

**添加 DNS Records** (DNS 生效后):
| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `@` (或 `www`) | `<project-name>.vercel.app` | Proxied |
| CNAME | `api` | `<backend-server-host>` | Proxied |

**SSL/TLS 设置**:
- Settings → SSL/TLS → Overview
- 加密模式: **Full (strict)**
- Edge Certificates → 开启 **Always Use HTTPS**

## 4. 注册完成后回填清单

在以下文件中填入注册获得的真实值:

- [ ] `test-platform-v2/config/runtime/production.env`
- [ ] `docs/测试平台全功能验收文档-环境链接与账号汇总.md`
- [ ] `test-platform-v2/deploy/cloudflare-dns-records.md`
- [ ] `test-platform-v2/deploy/supabase-setup.md`
- [ ] `test-platform-v2/deploy/production-architecture.md`

**必须替换的值**:
| 占位符 | 替换为 |
|--------|-------|
| `<supabase-db-password>` | Supabase 数据库密码 |
| `<project-ref>` | Supabase 项目引用 ID |
| `<vercel-deployment-domain>` | Vercel 部署域名 |
| `<generate-with-...>` | 运行 `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

## 5. 安全要求

- ⚠️ 数据库密码不得写入 Git
- ⚠️ SECRET_KEY 必须为强随机值
- ⚠️ production.env 必须保持 .gitignore 忽略状态
- ⚠️ 注册所用邮箱/密码建议记录在密码管理器，不在聊天中发送
