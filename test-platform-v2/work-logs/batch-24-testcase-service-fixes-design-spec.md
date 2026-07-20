# Batch 24 — Design Spec
> **Design (🎨)** | Date: 2026-07-20 | Status: 就绪（反向回填）

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（`bg-muted` / `text-muted-foreground` / `border` / `variant`）。
本批次为现有 UI 修正，无新增组件，仅修改现有组件属性。

## 1. 组件规格表

| 组件 | 修改点 | 变更前 | 变更后 |
|------|--------|--------|--------|
| `Select` (域) | placeholder | "按域筛选" | "全部域" |
| `Select` (域) | 默认项文本 | "全部" | "全部域" |
| `Select` (域) | value 绑定 | `selDomain \|\| undefined` | `selDomain`（空串可匹配 SelectItem） |
| `Select` (模块) | placeholder | "按模块筛选" | "全部模块" |
| `Select` (模块) | 默认项文本 | "全部" | "全部模块" |
| `Select` (优先级) | placeholder | "优先级" | "全部优先级" |
| `Select` (优先级) | 默认项文本 | "全部" | "全部优先级" |
| `TableCell` (前置条件) | 渲染方式 | 数组隐式 join（无分隔） | `<div>` 列表，`space-y-0.5`，`max-h-[72px]` 可滚动 |
| `TableCell` (操作步骤) | 渲染方式 | 同上 | 同上 |
| `TableCell` (预期结果) | 渲染方式 | 同上 | 同上 |
| `InputGroupInput` (搜索) | placeholder | "搜索标题/关键字"（不变，已正确） | 不变 |
| `Button` (搜索) | onClick | `setPage(1)` | `setPage(1); refetch()` |

## 2. 布局与响应式

无变化。表格列宽保持不变：模块名称 `w-[120px]`，前置条件 `w-[140px]`，操作步骤/预期结果 `w-[160px]`。步骤内容区添加 `max-h-[72px] overflow-y-auto` 防止撑高表格行。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 域 Select | 数据加载中显示骨架 | 无域时仅显示"全部域"选项 | Toast 提示 | N/A |
| 步骤渲染 | N/A（静态渲染） | 无内容显示 "-" | N/A | N/A |
| 删除按钮 | N/A | `!domainId` 时 `disabled` | Toast 提示 | N/A |

## 4. 设计 QA 走查发现

### ⚪ P3-1 表格行高不一致
`index.tsx:406-430` — 步骤内容改用 `max-h-[72px] overflow-y-auto` 后，含多步用例的行可能比无步骤用例的行高。**建议**：确认 `min-h` 是否满足设计一致，当前可接受。

### ⚪ P3-2 搜索按钮与 refetch 重复触发
`index.tsx:315` — 搜索按钮同时调 `setPage(1)` 和 `refetch()`，若 `page` 已是 1 则 `useApi` 可能因 page 未变而不触发，此时 `refetch()` 兜底。**建议**：可接受，后续考虑 debounce 统一。

## 5. 设计签核
结论：**通过** — 无 P0/P1/P2 设计问题。所有修改为属性级调整，不改变组件结构。
