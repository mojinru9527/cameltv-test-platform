# Batch 217 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
前端 shadcn/ui + Radix + Tailwind + CVA；语义 UI 入口 `@/ui`（PageShell/Card/Badge/Progress/Button/Input/Label/Textarea）。遵守 `cameltv-ui-conventions` 与 batch54 语义 token 守卫（禁止固定色板）。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 向导步骤条 | Badge + 文本 | 当前步 primary / 其它 secondary | hover |
| 任务表单 | Input/Label/Textarea | muted-foreground 说明 | focus ring |
| 方案条目 Card | rounded border p-3 | 置信度 Progress（primary） | hover + 操作按钮组 |
| 审核按钮 | sm | 采纳 primary / 修改 ghost / 追问 ghost / 删除 danger | disabled during loading |

## 2. 布局与响应式
- 单列卡片流；`<1024px` 仍单列，按钮组可换行；无横向滚动。
- `PageShell` 提供标题 + 内容区。

## 3. 状态设计核对（四态）
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 生成方案 | Button loading，toast | 空态提示「点击生成」 | toast.error + 保留已生成条目 | 任务未创建时不可步入 |

## 4. 设计 QA 走查发现（P0–P3）
### ⚪ P3-1 语义 token
首版使用 `text-amber-600`（固定色板）被 batch54 守卫拦截。→ **已改为 `text-muted-foreground`**（语义类）。
### ⚪ P3-2 Button variant 命名
`@/ui` Button 使用 `primary/secondary/ghost/danger`，非 shadcn 的 `default/outline/destructive`。→ **已对齐**。

## 5. 设计签核
结论：**通过**（3 步向导 + 审核面板消费 version_task API；无固定色板；无引擎术语暴露）。
