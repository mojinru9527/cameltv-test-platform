---
title: "ADR-0005: Zustand 替代 Redux 作为前端状态管理"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "frontend", "state-management", "zustand", "react"]
related: ["0006-shadcn-ui-over-antd.md", "0004-jwt-bcrypt-rbac-auth.md"]
---

# ADR-0005: Zustand 替代 Redux 作为前端状态管理

## 状态

✅ 已采纳

## 日期

2026-01

## 背景

v1 前端使用 @tanstack/react-query 管理服务端状态，但缺少客户端状态管理方案。

v2 需要选择客户端状态管理方案（鉴权态、当前项目、UI 状态）。

## 决策

采用 **Zustand** 作为前端状态管理：
- 轻量级（~1KB），无 Provider 包裹
- 内置 localStorage 持久化（用于 authStore）
- 与 React Hook 风格一致

不使用 Redux Toolkit。

## 后果

### 正面影响

- ✅ 极简 API，上手成本低
- ✅ 天然支持 localStorage 持久化，适合鉴权态
- ✅ 与 React 18 的 Hook 和 Concurrent Mode 兼容
- ✅ 按需订阅——组件只 re-render 其消费的 slice 变化

### 负面影响 / 权衡

- ⚠️ 相比 Redux Toolkit，缺少结构化的异步处理（createAsyncThunk），但本项目中异步逻辑在组件/hooks 中处理
- ⚠️ 没有 Redux DevTools 的时间旅行调试——但 Zustand 支持 Redux DevTools 中间件

## 弃选方案

### 方案 A: Redux Toolkit

- 优点：生态完善，中间件丰富，调试工具强大
- 缺点：模板代码多，概念负担重（slices、reducers、actions、selectors）
- 放弃原因：当前状态管理需求简单（主要是鉴权 + 项目切换），Redux 过重

### 方案 B: React Context + useReducer

- 优点：零依赖
- 缺点：性能问题（Provider 下全部 re-render），不支持持久化
- 放弃原因：不适合需要跨组件频繁访问的状态（如 currentProject）

## 关联

- 相关 ADR: [ADR-0006](0006-shadcn-ui-over-antd.md) (同时期的前端技术选型)
