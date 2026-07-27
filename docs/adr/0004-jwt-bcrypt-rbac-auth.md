---
title: "ADR-0004: JWT + BCrypt + RBAC 认证授权方案"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "auth", "jwt", "bcrypt", "rbac", "security"]
related: ["0003-frontend-backend-physical-separation.md", "0005-zustand-over-redux.md"]
---

# ADR-0004: JWT + BCrypt + RBAC 认证授权方案

## 状态

✅ 已采纳

## 日期

2025-12

## 背景

v1 没有认证系统，任何人都可以直接访问 API。v2 需要支持多用户、多项目、细粒度权限控制。

需要选择认证方案和授权模型。

## 决策

采用 **JWT (python-jose) + BCrypt + RBAC** 方案：
- 认证：无状态 JWT，不存储 session。BCrypt 哈希密码
- 授权：基于权限点 (permissions) 的 RBAC，角色聚合权限点
- 数据范围：三级（global 全局 / project 项目内 / self 本人）
- 多项目：用户通过 `current_project_id` 切换上下文

## 后果

### 正面影响

- ✅ 无状态 JWT 不需服务端 session 存储，水平扩展友好
- ✅ BCrypt 提供足够安全的密码哈希
- ✅ 三级数据范围精细控制：管理员看全局、PM 看项目内、执行者看自己的数据
- ✅ 多项目隔离——同一平台管理多个被测项目

### 负面影响 / 权衡

- ⚠️ JWT 无法主动撤销（除非引入黑名单）。折中：token 有效期较短（默认 8 小时）
- ⚠️ RBAC 的权限点粒度需要持续维护——权限点太多管理复杂，太少不够灵活

## 弃选方案

### 方案 A: Session-based 认证

- 缺点：需要存储 session，多实例部署时需共享 session store
- 放弃原因：增加运维复杂度

### 方案 B: OAuth2 / 第三方登录

- 缺点：内网环境可能不适用，增加依赖
- 放弃原因：当前阶段需求不复杂，后期可按需加入

## 关联

- 后端认证 API: [test-platform-v2/backend/app/api/v1/auth.py](../../test-platform-v2/backend/app/api/v1/auth.py)
- 后端系统 API: [test-platform-v2/backend/app/api/v1/system.py](../../test-platform-v2/backend/app/api/v1/system.py)
