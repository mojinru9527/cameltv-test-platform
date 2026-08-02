---
title: "Batch 63 Design Spec — 汇总问题遗留解决版本"
owner: "design-team"
created: "2026-08-02"
status: "ready"
batch: "63"
tags: ["design", "batch-63", "legacy-debt", "spec"]
related:
  - "batch-63-legacy-issue-closure-prd-summary.md"
  - "batch-63-legacy-issue-closure-pm-plan.md"
---

# Batch 63 — Design Spec

> **Design (🎨)** | Date: 2026-08-02 | Status: Ready

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground /
border / variant）。本批以**反向回填 + 对账**为主：多数改动是对既有页面的权限/状态/
布局收敛，不引入新组件体系。

## 1. 组件规格表（本批涉及）

| 组件/页面 | 变更点 | 交互态 |
|---|---|---|
| 菜单（MainLayout） | 成熟模块恢复入口；未完成模块显式 Badge | hover/focus 可见；active 高亮 |
| 命令面板（CommandPalette） | 覆盖全部成熟模块路由；无权限命令禁用并提示 | 输入过滤；Enter 导航 |
| 只读角色页面 | 写入口（新增/编辑/删除/执行/批量）隐藏或禁用 | disabled 态带 title 提示 |
| 批量删除确认 | 显示数量/项目范围/不可逆警告；取消零请求 | 确认按钮 loading；失败回滚提示 |
| 历史交互标注 | 已保存语义交互以可编辑占位区域回显；真实坐标保留 | 编辑态与原标注交互一致 |
| 搜索提交态（testplan/report） | draft 与 committed keyword 分离；按钮/回车提交 | 输入防抖不触发请求 |
| 知识中心桌面布局 | 标签可换行/可访问滚动；卡片响应式列数 | 1440 无横向溢出 |
| 触控目标 | 移动端关键按钮 ≥44px 触控面积 | 390×844 可点 |

## 2. 布局与响应式

| 断点 | 布局规则 |
|---|---|
| <768px | 单列；触控目标 ≥44px；表格横向滚动容器可聚焦 |
| 768–1024px | 双列上限；标签可换行 |
| ≥1024px | 知识中心标签自适应列数，最大宽度合理，无横向滚动 |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用/无权限(403/503) |
|---|---|---|---|
| 菜单/命令面板 | 骨架 | 显示"无匹配" | 错误可重试 | 禁用 + 提示权限 |
| 执行入口（五入口统一） | 统一 loading | 空结果态 | 统一错误态 | production guard 前置拒绝，零副作用 |
| 运营发布页（沿用 Batch 62） | Skeleton | 空态说明 | 503 显式 | production-deferred 提示 |

## 4. 设计 QA 走查发现（P0–P3）

### 🟡 P2-001 知识中心桌面标签溢出（承接 B60-P2-006）

`pages/knowledge/index.tsx` 标签行在 1440×900 下需横向滚动。
**建议**：标签容器 flex-wrap + 可访问滚动；卡片 grid-template-columns 响应式。

### 🟡 P2-002 移动端触控面积（承接 B60-P2-002）

报告/计划等页小按钮 <44px。
**建议**：关键操作按钮统一最小高度/命中区。

### 🟠 P1-003 只读角色写入口可见（承接 B60-P1-009）

testplan/requirement/report/schedule/environment/dataset/notify 页仍显示写入口。
**建议**：统一权限组件收敛；隐藏而非仅禁用，后端 403 保留。

### 🟠 P1-004 菜单/命令面板缺失（承接 B60-P1-002）

发布包/缺陷/数据集/集成被隐藏；命令面板漏多页。
**建议**：以 seed.py 权限清单为唯一基准生成菜单/命令，成熟模块恢复入口。

## 5. 设计签核

结论：**有条件通过**。P1-003/P1-004 为本批 Slice 4 必做；P2-001/P2-002 为 Slice 5 必做；
其余页面如发现新问题按同一规范补齐。
