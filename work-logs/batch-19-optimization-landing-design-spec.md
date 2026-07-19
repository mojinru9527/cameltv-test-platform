# Batch 19 — Design Spec
> **Design (🎨)** | Date: 2026-07-20 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。
所有组件沿用项目已有的 Radix Tabs、Collapsible、Badge、Select 等，不引入新依赖。

## 1. 组件规格表

### 1.1 AssetTab — 服务 Tab + 模块层级

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| TabsList | `h-auto max-w-full overflow-x-auto justify-start` | bg-muted, data-[state=active]:bg-background | 水平滚动，触控滑动 |
| TabsTrigger | `px-4 py-2 text-sm` | text-muted-foreground, data-[state=active]:text-foreground | default/hover/active/focus-visible:ring |
| 左右滚动按钮 | `h-8 w-8` icon-only | variant="ghost" | hover 时显示，overflow 时才渲染 |
| Collapsible (模块) | `w-full border-b` | border-border | 默认 closed，点击 toggle |
| CollapsibleTrigger | `px-4 py-2 flex items-center gap-2` | hover:bg-muted/50 | ChevronDown 图标旋转动画 |
| 接口行 | `px-4 py-1.5 text-sm` | hover:bg-accent | 显示 METHOD + path + description |

### 1.2 DebugTab — 地址拆分 + 响应移底

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 服务器地址 Input | `w-full` | variant="outline" | 环境切换时自动更新，可手动编辑 |
| 服务名 Input | `w-full` | variant="outline" | 手动输入 |
| 模块路径 Input | `w-full` | variant="outline" | 手动输入 |
| 接口路径 Input | `w-full` | variant="outline" | 手动输入 |
| 组装预览 | `text-xs text-muted-foreground mt-1` | mono font | 实时显示完整 URL 预览 |
| 响应面板 | 请求配置下方 `mt-4 w-full` | border rounded-lg | 从右侧 col-span-1 移到下方全宽 |

布局变化：
- Before: `grid grid-cols-1 lg:grid-cols-3` → 请求 2/3 + 响应 1/3
- After: 请求配置全宽 → 响应面板下方全宽

### 1.3 ApiCaseTab — 按接口分组

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| Collapsible (接口组) | `w-full border rounded-lg mb-2` | bg-card | 默认 closed |
| CollapsibleTrigger | `px-4 py-3 flex items-center justify-between` | hover:bg-muted/50 | ChevronDown + Badge (用例数) |
| 用例行 | `px-4 py-2 border-t flex items-center gap-3` | hover:bg-accent | 选择框 + 标题 + 执行按钮 |
| 接口组操作栏 | `flex gap-2` | — | "执行全部" 按钮 |
| 响应 Modal | `max-w-2xl` | — | 单条执行结果弹窗，可关闭 |

### 1.4 CaseDrawer — 步骤格式化

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 格式化视图 | `font-mono text-sm leading-relaxed` | bg-muted/30 rounded p-3 | 只读显示 |
| JSON 编辑 | `min-h-[120px] font-mono text-sm` | variant="outline" | 编辑模式 |
| 视图切换 | `variant="ghost" size="sm"` | — | 切换格式化/JSON 视图 |

### 1.5 用例列表 — 分页

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 分页大小 Select | `w-[80px]` | — | 20/50/100 三选项 |
| 表格容器 | `min-h-[600px]` | — | 防止切换分页时高度跳动 |

### 1.6 需求列表 — 来源压缩

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 来源单元格 | `max-w-[200px] truncate` | — | title 属性显示完整 URL |
| 蓝湖链接 | `text-sm` | text-blue-600 | 显示"蓝湖 v{版本号}" |
| 非蓝湖链接 | `text-sm` | text-muted-foreground | 显示域名 |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| < 768px (mobile) | 单列堆叠 | Tabs 水平滚动，Collapsible 全宽 |
| 768–1024px (tablet) | 双列 | DebugTab 拆分字段并排 |
| ≥ 1024px (desktop) | 全宽 | 所有组件最大宽度 |

## 3. 状态设计核对

| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| AssetTab | Skeleton 4 行 | "暂无接口资产，请先导入 Swagger" | Toast 错误提示 |
| DebugTab | 发送按钮 spinner | — | 响应面板显示错误信息 |
| ApiCaseTab | Skeleton 3 组 | "暂无接口用例，请先生成" | Toast 错误提示 |
| CaseDrawer | 步骤区域 Skeleton | "暂无步骤" placeholder | — |
| 用例列表 | 表格 Skeleton | "暂无用例" | Toast 错误提示 |
| 需求列表 | 表格 Skeleton | "暂无需求" | Toast 错误提示 |

## 4. 设计签核
结论：通过 — 所有改动沿用现有 shadcn/ui 组件，无新增依赖，无自定义 CSS，风格与项目一致。
