# Batch 20 — Design Spec
> **Design (🎨)** | Date: 2026-07-20 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。本次为**修复 batch-19 设计遗漏**，不引入新组件模式。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 优先级 Badge（独立列） | `px-2 py-0.5 text-xs rounded`，min-w-[56px] | P0=destructive / P1=orange-500 / P2=yellow-500 / P3=muted | 静态展示 |
| 接口资产 Tab（默认） | Tab 不变，仅改 defaultActive | 同现有 assets tab 样式 | 无需变更 |
| 路径显示（`/`→`-`） | `font-mono text-xs` | 同现有 code 样式 | 静态 |
| 备注列 | `max-w-[120px] truncate text-xs text-muted-foreground` | muted | hover 显示 tooltip 全文 |
| DebugTab 环境选择 | 同现有 Select 组件 | 同现有 | 初始化自动选中「测试5」 |

## 2. 布局与响应式

### 优先级列位置
```
| ☑ | 优先级 | 编号 | 标题 | 模块 | 状态 | 评审 | API | 操作 |
```
- 优先级列插在 checkbox 和编号之间
- 桌面：min-w-[72px]
- 平板（<1024px）：保持，Badge 缩小

### 接口资产备注列位置
```
| 方法 | 路径 | 摘要 | 模块 | 备注 | 操作 |
```
- 备注列在模块和操作之间
- 桌面：max-w-[120px] truncate
- 平板：隐藏备注列（responsive）

## 3. 状态设计核对

| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| 优先级列 | —（静态） | `—` 占位 | — |
| 备注列 | Skeleton 20px | `—` 占位 | — |
| DebugTab 默认环境 | 环境列表加载中 → disabled | 「无可用环境」→ placeholder | toast 提示 |

## 4. 设计 QA 走查发现

本次为修复性批次，无独立设计走查——所有 UI 变更沿用现有组件规范和主题系统。

### 确认项
- [x] 优先级 Badge 颜色与现有 Badge variant 一致
- [x] `/`→`-` 转换不影响调试 URL 拼接（仅展示层）
- [x] 备注列不影响表格列宽平衡
- [x] 默认 Tab 切换不破坏 Tab 切换动画

## 5. 设计签核
结论：**通过** — 9 项 UI 变更均为单点修复，无新增组件模式，沿用现有设计语言。
