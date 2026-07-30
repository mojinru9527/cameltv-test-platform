---
title: "Batch 58 PRD — 生产基础设施云注册"
owner: "product-team"
created: "2026-07-30"
status: "active"
batch: "58"
tags: ["prd", "production", "cloudflare", "vercel", "supabase", "batch-58"]
---

# Batch 58 PRD: 生产基础设施云注册

## 1. 问题陈述

### 现状
测试平台 v2 的生产环境处于 **UNPROVISIONED** 状态。`production.env.example` 中所有关键参数均为 `change-me-*` 占位符。生产部署所需的三个核心基础设施组件均未注册：

| 组件 | 当前状态 | 影响 |
|------|---------|------|
| DNS/CDN | 无 | 无生产域名，无 HTTPS，无 CDN 加速 |
| 前端托管 | Docker Nginx (自建) | 需自行维护服务器，无自动扩缩 |
| PostgreSQL | Docker 容器 (自建) | 需自行管理备份、高可用、安全补丁 |

### 用户痛点
- 测试平台只能在 localhost 访问，无法向外部用户展示
- 生产数据库无托管备份，数据丢失风险高
- TLS 证书需手动管理
- 前端部署需要完整的 Docker 环境

## 2. 成功指标

| # | 指标 | 目标 |
|---|------|------|
| M1 | Cloudflare 账号注册 + 站点添加 | ✅ 完成 |
| M2 | Vercel 项目创建 + 前端部署成功 | ✅ 完成 |
| M3 | Supabase 项目创建 + PostgreSQL 可用 | ✅ 完成 |
| M4 | `production.env` 配置完整 | 0 个 change-me 占位符 |
| M5 | 验收文档回填 | 三个平台的关键地址/连接信息全部录入 |

## 3. 非目标 (Non-Goals)

- ❌ **不执行生产部署**: 不将 Docker 服务实际迁移到云平台
- ❌ **不迁移现有数据**: 不在本批次执行数据库迁移
- ❌ **不配置 CI/CD**: Vercel 自动 Git 集成除外
- ❌ **不购买付费计划**: 三个平台均使用 Free Tier
- ❌ **不改造后端架构**: FastAPI 后端保持现有 Docker 部署方式不变

## 4. 用户故事

### US-01: 运维人员注册 Cloudflare DNS
**作为** 运维人员
**我想要** 在 Cloudflare 上注册域名并配置 DNS
**以便** 测试平台拥有生产级 HTTPS 和 CDN 加速

**验收标准**:
- Given Cloudflare 账号已创建
- When 添加站点并配置 DNS Records
- Then 域名解析生效，HTTPS 可访问

### US-02: 运维人员部署前端到 Vercel
**作为** 运维人员
**我想要** 将 React 前端部署到 Vercel
**以便** 前端获得自动构建、全球 CDN 和预览部署

**验收标准**:
- Given Vercel 账号已创建并关联 GitHub
- When push 到 main 分支
- Then 前端自动构建并部署到 `<project>.vercel.app`

### US-03: 运维人员在 Supabase 创建生产数据库
**作为** 运维人员
**我想要** 在 Supabase 上创建托管 PostgreSQL 实例
**以便** 获得自动备份、连接池和安全管理

**验收标准**:
- Given Supabase 项目已创建
- When 运行 Alembic 迁移
- Then 数据库 schema 创建成功，后端可连接

### US-04: QA 人员获得完整生产验收文档
**作为** QA 人员
**我想要** 在验收文档中查到所有生产基础设施的真实地址
**以便** 后续批次可以直接引用这些地址进行生产验收

**验收标准**:
- Given 三个平台注册完成
- When 查阅验收文档
- Then Cloudflare/Vercel/Supabase 的关键连接信息全部可查

## 5. 约束条件

| # | 约束 | 说明 |
|---|------|------|
| C1 | Free Tier Only | 本批次不产生任何费用 |
| C2 | 安全第一 | 密码/Token 不入 Git，仅写入 `.gitignore` 的 `production.env` |
| C3 | 文档同步 | 注册完成后立即回填验收文档 |
| C4 | 不破坏现有 | Docker Compose 部署方式保持可用 |

## 6. 关联条件

| 条件编号 | 描述 | 本批次处理 |
|---------|------|----------|
| C31-2 | 人工审查者确认 | 注册完成后需确认 |
| -- | P01-P10 生产固定配置 | 本批次填入真实值 |
| -- | DEFERRED/UNPROVISIONED | 本批次解除 |

## 7. C-Conditions 检查

> 本批次无来自上一批次 Leader 的 C 条件。Batch 57 Leader Verdict 未设定跨批次 C 条件。
> 本批次为基础设施注册任务，主要接触外部服务注册页面，不涉及 `test-platform-v2/` 代码修改（仅新增配置文件）。
