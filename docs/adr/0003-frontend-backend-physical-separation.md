---
title: "ADR-0003: 前后端物理隔离架构"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "architecture", "frontend-backend-separation", "ci-cd"]
related: ["0001-use-python-fastapi-monostack.md", "0004-jwt-bcrypt-rbac-auth.md"]
---

# ADR-0003: 前后端物理隔离架构

## 状态

✅ 已采纳

## 日期

2025-12

## 背景

v1 采用单体架构，前后端混在一个目录中。虽然代码上分离了 `server/` 和 `web-ui/`，但：
- 同一个 Docker Compose 文件管理所有服务
- 前端 proxy 到后端，但不支持独立部署
- CI/CD 是整体构建，前端改一行也要跑全量后端测试

v2 重构时，需决定前后端的代码组织和部署关系。

## 决策

采用 **前后端物理隔离 + 独立 CI/CD** 架构：
- `backend/` 和 `frontend/` 为独立子项目，各有独立的 `Dockerfile` 和 `package.json`/`requirements.txt`
- 前端通过 Nginx 反代 `/api` 到后端，静态文件由 Nginx 托管
- 前后端各自有独立的 CI 阶段（Backend Lint/Test → Frontend TypeCheck/Test+Build）
- 仅通过 REST API (JSON) 通信，后端不渲染 HTML，前端不直连数据库

## 后果

### 正面影响

- ✅ 前后端可独立开发、测试、部署
- ✅ CI/CD 精确感知变更范围——仅前端变更时跳过 Backend Test
- ✅ 前端可独立使用 Mock Server 开发，不依赖后端环境
- ✅ 后端 API 契约（OpenAPI JSON）是唯一真相源

### 负面影响 / 权衡

- ⚠️ CORS 配置和部署拓扑比单体复杂
- ⚠️ 需要维护两套 Dockerfile 和 CI 配置
- ⚠️ API 契约变更时需要前后端同步（通过 `gen:api` 命令自动化）

## 弃选方案

### 方案 A: 保持单体但代码分离

- 缺点：部署粒度太粗，CI/CD 无法精确控制
- 放弃原因：与 v2 "前后端分离" 目标矛盾

### 方案 B: BFF 模式（Backend For Frontend）

- 缺点：多一层中间层，维护成本高
- 放弃原因：当前业务复杂度不需要 BFF

## 关联

- 重构方案文档：[测试平台-前后端分离重构方案.md](../../测试平台-前后端分离重构方案.md)
- 相关 ADR: [ADR-0001](0001-use-python-fastapi-monostack.md)
