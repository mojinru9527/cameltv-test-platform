# Batch 50 — Design Spec

> **Design (🎨)** | Date: 2026-07-28 | Status: 就绪

## 0. 技术体系确认

- **组件库**: shadcn/ui (Radix + Tailwind + CVA) → **迁移到** `@/ui` Obsidian Flow 基元
- **CSS 体系**: `obsidian-flow.css` — 通过 `[data-ui-theme="obsidian-flow"]` 属性选择器作用域
- **Token 层**: CSS 自定义属性（`--_bg`, `--_surface`, `--_primary`, `--_text` 等），由 `UiThemeProvider` 挂载到 `<html>`
- **UI 组件参考**: `f:\CamelTv\test-platform-v2\frontend\src\ui\index.ts` — 统一导出 barrel

## 1. 组件替换映射表

### 1.1 基础组件 (Primitives)

| 旧组件 (shadcn) | 新组件 (`@/ui`) | 替换规则 |
|-----------------|-----------------|---------|
| `<Button variant="default">` | `<Button variant="primary">` | `default` → `primary`, 其他 variant 名一致 |
| `<Button variant="secondary">` | `<Button variant="secondary">` | 直接替换 import |
| `<Button variant="ghost">` | `<Button variant="ghost">` | 直接替换 import |
| `<Button variant="destructive">` | `<Button variant="danger">` | `destructive` → `danger` |
| `<Button variant="outline">` | `<Button variant="secondary">` | outline 无对应 → secondary |
| `<Button size="sm">` | `<Button size="sm">` | 直接映射 |
| `<Button size="default">` | `<Button size="md">` | `default` → `md` |
| `<Button size="lg">` | `<Button size="lg">` | 直接映射 |
| `<Badge variant="default">` | `<Badge variant="neutral">` | 语义映射 |
| `<Badge variant="secondary">` | `<Badge variant="neutral">` | 语义映射 |
| `<Badge variant="destructive">` | `<Badge variant="danger">` | 语义映射 |
| `<Badge variant="outline">` | `<Badge variant="neutral">` | 语义映射 |
| `<Input>` | `<Input>` | 直接替换 import，API 兼容 |
| shadcn Progress | `@/ui` Progress | 直接替换 import |
| shadcn Card | `<div className="ui-surface">` | CSS 类替代组件 |

### 1.2 语义组件 (Semantic)

| 组件 | 来源 | 目标页面 | 用途 |
|------|------|---------|------|
| `MetricStrip` | `@/ui` | Workbench | 顶部指标卡片行（合格率/覆盖率/缺陷数/通过率） |
| `SpatialChain` | `@/ui` | Trace | 需求→用例→计划→执行→缺陷→报告 空间质量链 |
| `StatusBadge` | `@/ui` | Defect | P0-P3 缺陷等级彩色标记 |
| `Inspector` | `@/ui` | PlanDetail, ReviewPage | 详情面板（可选集成） |
| `PageShell` | `@/ui` | 全部列表页 | 统一页面壳（面包屑 + 标题 + 操作区 + 状态线） |

### 1.3 ESLint/TS 注意

替换 import 时注意：
- shadcn Button: `import { Button } from '@/components/ui/button'` → `import { Button } from '@/ui'`
- shadcn Badge: `import { Badge } from '@/components/ui/badge'` → `import { Badge } from '@/ui'`
- shadcn Input: `import { Input } from '@/components/ui/input'` → `import { Input } from '@/ui'`
- 如果页面同时需要 shadcn 其他组件（`Table`, `Select`, `Dialog` 等），保留 shadcn import，仅替换上述基元

## 2. CSS 类应用指南

### 2.1 表面层级

```
┌─────────────────────────────────────────┐
│ .ui-glass                               │  ← Chrome/侧边栏/Inspector（玻璃态）
│ ┌─────────────────────────────────────┐ │
│ │ .ui-surface-elevated               │ │  ← 选中卡片/Popover（提亮）
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ .ui-surface                     │ │ │  ← 内容卡/表格/表单（暗色平面）
│ │ │                                 │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
        背景: [data-ui-theme] body (--_bg)
```

### 2.2 页面标准结构

```html
<!-- 使用 ObsidianListPage 的页面自动获得此结构 -->
<div class="obsidian-list-page">            <!-- ObsidianListPage 根 -->
  <div class="... kicker + title ...">      <!-- 页面标题区 -->
  <div class="ui-surface ui-spotlight">     <!-- 内容区 — 替换 Card -->
    <!-- 页面内容：表格/表单/卡片 -->
    <table class="ui-table">...</table>     <!-- 替换 shadcn Table 样式 -->
    <button class="ui-btn ui-btn-primary">  <!-- 替换 shadcn Button -->
      新建
    </button>
    <span class="ui-badge ui-badge-success"> <!-- 替换 shadcn Badge -->
      PASS
    </span>
  </div>
</div>
```

### 2.3 页面级 CSS 类清单

| 场景 | 应用于 | CSS 类 |
|------|--------|--------|
| 内容卡片/面板 | 原 `<Card>` 组件 | `ui-surface` |
| 玻璃面板 | 侧边栏/Inspector/Header | `ui-glass` |
| Spotlight 交互 | 内容区容器 | `ui-spotlight` |
| 数据表格 | 原 `<Table>` | `ui-table` |
| 操作按钮 | 所有按钮 | `ui-btn ui-btn-{variant}` |
| 状态标记 | 所有 Badge | `ui-badge ui-badge-{status}` |
| 输入框 | 所有 Input | `ui-input` |
| 进度条 | 所有 Progress | `ui-progress` + `ui-progress-fill` |

## 3. 布局与响应式

### 3.1 ObsidianListPage 布局（列表页标准）

```
┌──────────────────────────────────────────────────┐
│ ── green kicker line ──  subtitle (optional)     │
│                                                  │
│ 页面标题 (dark title)     [刷新] [操作按钮区]     │
│ 描述文字 (muted)                                 │
│                                                  │
│ [筛选栏 — filterBar slot]                        │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ .ui-surface (.ui-spotlight)                  │ │
│ │                                              │ │
│ │  [数据表格 / 卡片列表 / 表单]                 │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### 3.2 断点

| 断点 | 布局 | 侧边栏 | 内容区 |
|------|------|--------|--------|
| < 768px (mobile) | 单列 | 隐藏 (Sheet overlay) | 全宽 |
| 768-1024px (tablet) | 单列 | 折叠 (icon only) | 全宽 |
| ≥ 1024px (desktop) | 侧边栏 + 内容 | 展开 (240px) | `max-w-[1440px] mx-auto` |

## 4. 状态设计核对

| 组件 | Loading | Empty | Error | Disabled |
|------|---------|-------|-------|----------|
| ObsidianListPage | Skeleton 卡片 (`.ui-surface` + `animate-pulse`) | 空态插图 + "暂无数据" + 创建引导 | Alert 卡片 (`.ui-badge-danger` + 重试按钮) | N/A |
| Button | 禁用 + Spinner 图标 | N/A | N/A | `opacity: 0.38` + `cursor: not-allowed` |
| Badge | N/A | N/A | N/A | N/A |
| Input | N/A | placeholder 文字 | `.is-error` 红色边框 | `opacity: 0.38` |
| MetricStrip | Skeleton 数字块 | "--" 占位符 | "--" 占位符 | N/A |
| SpatialChain | 虚线连接动画 | 空链 + "暂无追溯数据" | 断链图标 | N/A |

## 5. 设计 QA 走查发现

### 🔴 P0-1: 主应用页面未使用 Obsidian Flow 组件
**文件**: `frontend/src/pages/*/index.tsx` (14 个页面)
**事实**: `@/ui` 导出的 `PageShell`, `SpatialChain`, `Inspector`, `MetricStrip`, `StatusBadge`, `Button`, `Badge`, `Input`, `Progress` 零页面导入使用。页面内仍然是 shadcn 组件。
**建议**: 按 PM Plan Task 1-4 逐页面替换。

### 🔴 P0-2: Environment 页面完全未接入 Obsidian Flow
**文件**: `frontend/src/pages/environment/index.tsx`
**事实**: 唯一不导入任何 `@/ui` 内容的页面，纯 shadcn 组件渲染。
**建议**: 立即接入 `useObsidianPage` + ObsidianListPage + `@/ui` 基元。

### 🟠 P1-1: 页面内 Card 组件未使用 .ui-surface
**文件**: 7 个已接入 ObsidianListPage 的页面
**事实**: `ObsidianListPage` 提供了外层暗色容器，但内部的 `<Card>` 仍使用 shadcn 白色背景。
**建议**: 将 `<Card>` 替换为 `<div className="ui-surface">`，或给 Card 添加 `className="ui-surface"`。

### 🟠 P1-2: MetricStrip 在 Workbench 不可见
**文件**: `frontend/src/pages/workbench/index.tsx`
**事实**: `obsidianMetrics` 数据已构建但仅在 `ObsidianWorkbench` 的 `metrics` prop 中传入，未使用独立的 `MetricStrip` 组件渲染在页面顶部。
**建议**: 在 Workbench 内容区顶部显式渲染 `<MetricStrip>`。

### 🟡 P2-1: 表格未使用 .ui-table 类
**文件**: 所有使用 shadcn Table 的页面
**事实**: shadcn Table 有自己的一套样式（白色背景 + 灰色分割线），与 obsidian-flow 暗色背景不协调。
**建议**: 给 `<Table>` 添加 `className="ui-table"`。

### 🟡 P2-2: MainLayout 侧边栏玻璃态是内联 style
**文件**: `frontend/src/layouts/MainLayout.tsx`
**事实**: obsidian-flow 模式下侧边栏通过 `<style>` 标签注入内联 CSS 实现玻璃效果，应该使用 `ui-glass` 类。
**建议**: 改为给侧边栏元素添加 `className="ui-glass"`。

## 6. 设计签核

**结论**: 有条件通过 — P0 项必须在 Dev 阶段全部修复；P1 项本轮修复；P2 项可延至下一 batch。
