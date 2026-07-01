---
title: "ADR-0006: shadcn/ui 替代 Ant Design 作为 v2 前端 UI 库"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "frontend", "ui-library", "shadcn-ui", "tailwind"]
related: ["0005-zustand-over-redux.md", "0003-frontend-backend-physical-separation.md"]
---

# ADR-0006: shadcn/ui 替代 Ant Design 作为 v2 前端 UI 库

## 状态

✅ 已采纳

## 日期

2026-01

## 背景

v1 前端使用 Ant Design 5，提供了丰富的企业级组件。但在实际使用中发现：
- Ant Design 的 Design Token 定制体系复杂，与 Tailwind 风格冲突
- 组件源码不可控——定制行为需要通过各种 props，深层行为无法修改
- Bundle 体积较大（Tree shaking 不完全）
- v2 前端采用 Tailwind CSS，Ant Design 的 CSS-in-JS 方案与 Tailwind 不兼容

## 决策

采用 **shadcn/ui（Radix UI + Tailwind CSS）** 替代 Ant Design：
- 组件源码由 CLI 直接复制到 `src/components/ui/`，完全可控
- 基于 Radix UI 原语，无障碍（a11y）优先
- 与 Tailwind CSS 天然兼容，统一的样式体系
- 按需引入，不增加未使用组件的 Bundle 体积

## 后果

### 正面影响

- ✅ 组件源码完全可控，可自由定制
- ✅ 与 Tailwind CSS 完美配合，一套样式体系
- ✅ Radix UI 的无障碍标准（符合 WCAG）
- ✅ 按需引入，小 Bundle
- ✅ 社区活跃，组件数量持续增长

### 负面影响 / 权衡

- ⚠️ 与 Ant Design 相比，缺少部分高级组件（如 ProTable、SchemaForm），需要自行组合
- ⚠️ 上手成本——需要同时理解 Radix UI 原语和 Tailwind
- ⚠️ shadcn/ui 不是传统 npm 包，是源码复制模式——升级时需手动处理

## 弃选方案

### 方案 A: 保持 Ant Design 5

- 优点：组件丰富，文档完善，已有 v1 经验
- 缺点：与 Tailwind CSS 不兼容，组件定制受限，Bundle 体积大
- 放弃原因：v2 的 UI 风格和架构与 v1 不同，需要更灵活的组件方案

### 方案 B: MUI (Material UI)

- 优点：成熟的企业级组件库
- 缺点：Material Design 风格与 CamelTv 品牌差异大，定制成本高
- 放弃原因：视觉风格差异大

### 方案 C: 纯 Tailwind + Headless UI

- 优点：最灵活
- 缺点：需要从头实现组件逻辑，开发效率低
- 放弃原因：shadcn/ui 在 Radix 之上提供了开箱即用的样式，是更好的平衡点

## 关联

- 相关 ADR: [ADR-0005](0005-zustand-over-redux.md) (同时期的前端技术选型)
- 前端 CLAUDE.md: [test-platform-v2/frontend/CLAUDE.md](../../test-platform-v2/frontend/CLAUDE.md)
