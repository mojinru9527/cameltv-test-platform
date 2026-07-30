---
title: "Batch 58 PM Plan — 生产基础设施云注册"
owner: "pm-team"
created: "2026-07-30"
status: "active"
batch: "58"
tags: ["pm", "production", "cloudflare", "vercel", "supabase", "batch-58"]
---

# Batch 58 PM Plan: 生产基础设施云注册

## 任务拆解

### Slice 1: Supabase — PostgreSQL 数据库注册

| 字段 | 内容 |
|------|------|
| **任务** | 在 Supabase 注册账号，创建项目，获得 PostgreSQL 连接串 |
| **预估** | 15 min |
| **验收标准** | 1) Supabase 项目创建成功 2) 数据库连接串可用 3) `production.env` 中 DATABASE_URL 已填入真实值 |
| **涉及文件** | `test-platform-v2/config/runtime/production.env`, `test-platform-v2/deploy/supabase-setup.md` |
| **参考** | `test-platform-v2/docs/Batch58生产基础设施注册操作单.md` §1 |

### Slice 2: Vercel — 前端部署注册

| 字段 | 内容 |
|------|------|
| **任务** | 在 Vercel 注册账号，导入 GitHub 仓库，部署前端 |
| **预估** | 15 min |
| **验收标准** | 1) Vercel 项目创建成功 2) 前端成功部署到 `<project>.vercel.app` 3) `vercel.json` 配置正确 4) `production.env` 中 PLATFORM_FRONTEND_URL 已填入 |
| **涉及文件** | `test-platform-v2/frontend/vercel.json`, `test-platform-v2/config/runtime/production.env` |
| **参考** | `test-platform-v2/docs/Batch58生产基础设施注册操作单.md` §2 |

### Slice 3: Cloudflare — DNS/CDN 注册

| 字段 | 内容 |
|------|------|
| **任务** | 在 Cloudflare 注册账号，添加站点，配置 DNS Records |
| **预估** | 20 min |
| **验收标准** | 1) Cloudflare 账号创建成功 2) 站点添加成功 3) DNS CNAME 记录指向 Vercel 4) SSL/TLS Full (strict) 已配置 |
| **涉及文件** | `test-platform-v2/deploy/cloudflare-dns-records.md`, `test-platform-v2/deploy/production-architecture.md` |
| **参考** | `test-platform-v2/docs/Batch58生产基础设施注册操作单.md` §3 |

### Slice 4: 配置整合与文档回填

| 字段 | 内容 |
|------|------|
| **任务** | 将三个平台注册信息整合到 production.env 和验收文档 |
| **预估** | 20 min |
| **验收标准** | 1) `production.env` 0 个 change-me 占位符 2) 验收文档已回填所有三个平台的连接信息 3) 部署架构文档已更新为真实值 |
| **涉及文件** | `test-platform-v2/config/runtime/production.env`, `docs/测试平台全功能验收文档-环境链接与账号汇总.md`, `test-platform-v2/deploy/production-architecture.md` |
| **参考** | 注册操作单 §4 回填清单 |

### Slice 5: QA 自检

| 字段 | 内容 |
|------|------|
| **任务** | 验证所有配置文件、文档一致性、安全合规 |
| **预估** | 15 min |
| **验收标准** | 1) `production.env.example` 与 `production.env` 结构一致 2) 无秘密值泄露到 Git 3) 验收文档链接可追溯 |
| **涉及文件** | 全部产出文件 |
| **参考** | 本批次 QA Report |

## 总预估: ~85 min (5 slices)

## 依赖关系

```
Slice 1 (Supabase) ──┐
                      ├──> Slice 4 (整合回填) ──> Slice 5 (QA)
Slice 2 (Vercel) ────┤
                      │
Slice 3 (Cloudflare) ─┘
```

Slice 1-3 可并行执行（相互独立），Slice 4 依赖前三者完成，Slice 5 为最终检查。

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 域名未就绪 | 中 | Cloudflare 站点添加需真实域名 | 使用 Vercel/Supabase 提供的免费子域名先行 |
| 邮箱验证延迟 | 低 | 注册流程阻塞 | 提前准备多个邮箱 |
| GitHub OAuth 授权范围 | 低 | Vercel 需访问仓库 | 仅授权 `mojinru9527/cameltv-test-platform` |
