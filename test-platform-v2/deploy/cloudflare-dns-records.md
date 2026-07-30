---
title: "Cloudflare DNS Records — CamelTv 测试平台生产环境"
owner: "devops-team"
created: "2026-07-30"
status: "draft"
tags: ["cloudflare", "dns", "production", "batch-58"]
---

# Cloudflare DNS Records — 测试平台生产环境

> ⚠️ 本文档中的域名和 IP 地址为占位符。注册 Cloudflare 并添加站点后回填真实值。

## 1. 域名规划

| 用途 | 域名 | Cloudflare 记录类型 |
|------|------|-------------------|
| 测试平台前端 (Vercel) | `<platform-frontend-domain>` | CNAME → `cname.vercel-dns.com` |
| 测试平台后端 API | `<platform-backend-domain>` | A/CNAME → 后端服务器 IP |
| 根域名跳转 | `<root-domain>` | CNAME → 前端域名 |

## 2. DNS Records

### 前端 (Vercel)

```
Type: CNAME
Name: <platform-subdomain>
Target: cname.vercel-dns.com
Proxy status: Proxied (CDN enabled)
TTL: Auto
```

### 后端 API

```
Type: A (或 CNAME)
Name: backend.<platform-domain>
Target: <backend-server-ip>
Proxy status: Proxied (CDN enabled)
TTL: Auto
```

## 3. Cloudflare 注册步骤

1. 访问 https://dash.cloudflare.com/sign-up 注册账号
2. 添加站点 (Add Site) — 输入你的域名
3. 选择 Free Plan
4. 将域名 DNS 服务器更换为 Cloudflare 提供的 NS 地址
5. 等待 DNS 生效后，按上表添加 DNS Records
6. SSL/TLS 设置: **Full (strict)**
7. Edge Certificates: 开启 **Always Use HTTPS**

## 4. 注册后回填

注册完成后，将以下信息回填到:
- `test-platform-v2/config/runtime/production.env` (`PLATFORM_FRONTEND_URL`, `ALLOWED_ORIGINS`)
- `docs/测试平台全功能验收文档-环境链接与账号汇总.md` (Section 2 测试平台自身)

| 字段 | 值 |
|------|-----|
| Cloudflare 账号邮箱 | `<registered-email>` |
| 站点域名 | `<site-domain>` |
| 前端 FQDN | `https://<platform-frontend-domain>` |
| 后端 FQDN | `https://backend.<platform-domain>` |
| DNS NS 记录 | `<cloudflare-assigned-ns>` |
