# Batch 51 — PRD 概要

> 🟦 Product | Date: 2026-07-28

## 问题陈述

Batch-50 完成了 Obsidian Flow CSS 主题变量覆写 + Button/Input/Progress 三大基元替换。但 CI `tsc --noEmit` 揭示大量遗漏：
- **187 处** Badge 仍用 shadcn `variant` prop（`@/ui` Badge 只认 `tone`）
- **0 页面**使用 PageShell（统一列表页框架未落地）
- **Card/Textarea/Label/Select/Skeleton** 等高频 shadcn 组件尚无 `@/ui` 等价物
- `tsc --noEmit` 有预存 `deep-eql` 类型定义缺失

## 成功指标

1. `@/ui` Badge `tone` 替代 shadcn Badge `variant`，覆盖率 ≥90%
2. 新增 ≥5 个 `@/ui` 基元（Card/Textarea/Label/Select/Skeleton）
3. PageShell 覆盖 ≥5 个列表页
4. `tsc --noEmit` 零错误（处理 deep-eql）
5. Vite 构建零错误

## 非目标

- 不做 Dialog/Sheet/Sidebar 迁移（复杂度高，依赖 Radix Portal）
- 不做 Avatar/Switch/Checkbox 迁移（低优先级）
- 不做 Separator/ScrollArea 迁移（已可用 CSS 替代）

## 用户故事

### US-1: Badge 全量 tone 迁移
**作为** 平台用户  
**我想要** 所有 Badge 标签使用 obsidian-flow 翡翠绿语义色调  
**以便** 整个平台视觉效果统一  

**验收标准**:
- Given 任意页面的 Badge，When 渲染，Then 使用 `tone` prop（非 `variant`）
- Given 动态 variant 表达式 `{x ? 'default' : 'destructive'}`，When 迁移，Then 映射为 `{x ? 'neutral' : 'danger'}`
- Given `variant="outline"`，When 迁移，Then 映射为 `tone="neutral"`

### US-2: 新增 @/ui 基元
**作为** 开发者  
**我想要** 从 `@/ui` 导入常用表单/展示组件  
**以便** 不需要混用 `@/components/ui/*` 和 `@/ui`

**验收标准**:
- Given `Card`，When 使用，Then 自动应用 `.ui-surface` 样式
- Given `Textarea`，When 使用，Then 符合 obsidian-flow 输入框规范
- Given `Label`，When 使用，Then 使用 _text-secondary 颜色
- Given `Select`（仅 trigger/content/item），When 使用，Then 匹配 Button/Input 视觉风格
- Given `Skeleton`，When 使用，Then 使用 _surface-elevated 闪烁

### US-3: PageShell 列表页统一
**作为** 平台用户  
**我想要** 列表页有统一的标题/副标题/操作栏布局  
**以便** 在不同模块间有一致的导航体验

**验收标准**:
- Given 列表页（testcase/environment/defect/testplan/report），When 访问，Then 使用 PageShell 布局
- Given PageShell，When 渲染，Then 提供 title/subtitle/actions 插槽

### US-4: tsc 零错误
**作为** 开发者  
**我想要** `tsc --noEmit` 无错误  
**以便** CI 门禁可以通过

**验收标准**:
- Given `npx tsc --noEmit`，When 执行，Then 退出码 0
